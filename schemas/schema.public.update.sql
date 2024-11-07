-- Assuming version at least 0.3.0

----------------
-- Ayon 0.3.1 --
----------------

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'bundles'
        AND column_name = 'is_archived'
    ) THEN
        ALTER TABLE IF EXISTS bundles
        ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END $$;


----------------
-- Ayon 0.4.0 --
----------------

-- Add is_dev column to bundles
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'bundles'
        AND column_name = 'is_dev'
    ) THEN
        ALTER TABLE IF EXISTS bundles
        ADD COLUMN is_dev BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END $$;

DROP TABLE IF EXISTS public.addon_versions; -- replaced by bundles
DROP TABLE IF EXISTS public.dependency_packages; -- stored as json files


-- Delete project-level roles. They are hard to migrate,
-- so users will have to re-create them (collateral damage, sorry)
CREATE OR REPLACE FUNCTION delete_project_roles ()
   RETURNS VOID  AS
   $$
   DECLARE rec RECORD;
   BEGIN
       -- Get all the schemas
        FOR rec IN
        select distinct nspname
         from pg_namespace
         where nspname like 'project_%'
           LOOP
             EXECUTE 'DROP TABLE IF EXISTS ' || rec.nspname || '.roles';
           END LOOP;
           RETURN;
   END;
   $$ LANGUAGE plpgsql;

SELECT delete_project_roles();
DROP FUNCTION IF EXISTS delete_project_roles();

-- Rename roles table to access_groups
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'access_groups') THEN
    ALTER TABLE IF EXISTS public.roles RENAME TO access_groups;
  ELSE
    DROP TABLE IF EXISTS public.roles;
  END IF;
END $$;

-- Create access_groups table in all project schemas
CREATE OR REPLACE FUNCTION create_access_groups_in_projects ()
   RETURNS VOID  AS
   $$
   DECLARE rec RECORD;
   BEGIN
        FOR rec IN select distinct nspname from pg_namespace where nspname like 'project_%'
        LOOP
             EXECUTE 'CREATE TABLE IF NOT EXISTS '
            || rec.nspname ||
            '.access_groups(name VARCHAR PRIMARY KEY REFERENCES public.access_groups(name), data JSONB NOT NULL DEFAULT ''{}''::JSONB)';
        END LOOP;
        RETURN;
   END;
   $$ LANGUAGE plpgsql;

SELECT create_access_groups_in_projects();
DROP FUNCTION IF EXISTS create_access_groups_in_projects();


----------------
-- Ayon 0.4.8 --
----------------

-- Add is_dev column to bundles
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'bundles'
        AND column_name = 'active_user'
    ) THEN
        ALTER TABLE IF EXISTS bundles
        ADD COLUMN active_user VARCHAR REFERENCES public.users(name) ON DELETE SET NULL;

    END IF;
END $$;

-- Check again for the active_user column, because it might have been created in the
-- previous step.
-- But if bundle table still does not exist, let the public.schema.sql create it later
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'bundles'
        AND column_name = 'active_user'
    ) THEN
        CREATE UNIQUE INDEX IF NOT EXISTS bundle_active_user_idx
        ON public.bundles(active_user) WHERE (active_user IS NOT NULL);
    END IF;
END $$;


DROP TABLE IF EXISTS public.addon_versions; -- replaced by bundles
DROP TABLE IF EXISTS public.dependency_packages; -- stored as json files

---------------
-- Ayon 0.6 --
---------------

-- To every project project schema, add thumbnail_id column to tasks table
-- and create a foreign key constraint to the thumbnails table

CREATE OR REPLACE FUNCTION add_thumbnail_id_to_tasks ()
   RETURNS VOID  AS
   $$
   DECLARE rec RECORD;
   BEGIN
        FOR rec IN select distinct nspname from pg_namespace where nspname like 'project_%'
        LOOP
             EXECUTE
              'ALTER TABLE IF EXISTS ' || rec.nspname || '.tasks ' ||
              'ADD COLUMN IF NOT EXISTS thumbnail_id UUID ' ||
              'REFERENCES ' || rec.nspname || '.thumbnails(id) ON DELETE SET NULL';
        END LOOP;
        RETURN;
   END;
   $$ LANGUAGE plpgsql;

SELECT add_thumbnail_id_to_tasks();
DROP FUNCTION IF EXISTS add_thumbnail_id_to_tasks();

-------------------
-- Ayon 1.0.0-RC --
-------------------

-- Copy siteId to instanceId, if instanceId does not exist
-- (this is a one-time migration)


DO $$
BEGIN
    -- Check if the 'config' table exists
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'config') THEN

        INSERT INTO config (key, value)
        SELECT 'instanceId', value
        FROM config
        WHERE key = 'siteId'
        AND NOT EXISTS (
            SELECT 1
            FROM config
            WHERE key = 'instanceId'
        );
    END IF;
END $$;

--------------------
-- Ayon 1.0.0-RC5 --
--------------------

-- refactor links

CREATE OR REPLACE FUNCTION refactor_links() RETURNS VOID  AS
$$
DECLARE rec RECORD;
BEGIN
  FOR rec IN select distinct nspname from pg_namespace where nspname like 'project_%'
  LOOP
    IF NOT EXISTS(
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = rec.nspname
      AND table_name = 'links'
      AND column_name = 'name'
    )
    THEN
      -- project links table does not have name column, so we need to create it
      -- and do some data migration
      RAISE WARNING 'Refactoring links in %', rec.nspname;
      EXECUTE 'SET LOCAL search_path TO ' || quote_ident(rec.nspname);

      ALTER TABLE IF EXISTS links ADD COLUMN name VARCHAR;
      ALTER TABLE links RENAME COLUMN link_name TO link_type;
      ALTER TABLE links ADD COLUMN author VARCHAR NULL;
      UPDATE links SET author = data->>'author';

      DROP INDEX link_unique_idx;
    END IF;
  END LOOP;
  RETURN;
END;
$$ LANGUAGE plpgsql;

SELECT refactor_links();
DROP FUNCTION IF EXISTS refactor_links();


----------------
-- Ayon 1.0.8 --
----------------

CREATE EXTENSION IF NOT EXISTS "pg_trgm";
ALTER EXTENSION pg_trgm SET SCHEMA public;

-- Create activities tables in all project schemas
CREATE OR REPLACE FUNCTION create_activity_feed_in_projects ()
   RETURNS VOID  AS
   $$
   DECLARE rec RECORD;
   BEGIN
        FOR rec IN select distinct nspname from pg_namespace where nspname like 'project_%'
        LOOP
            EXECUTE 'SET LOCAL search_path TO ' || quote_ident(rec.nspname);

            CREATE TABLE IF NOT EXISTS activities (
                id UUID PRIMARY KEY,
                activity_type VARCHAR NOT NULL,
                body TEXT NOT NULL,
                data JSONB NOT NULL DEFAULT '{}'::JSONB,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                creation_order SERIAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_activity_type ON activities(activity_type);

            CREATE TABLE IF NOT EXISTS activity_references (
                id UUID PRIMARY KEY, -- generate uuid1 in python
                activity_id UUID NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
                reference_type VARCHAR NOT NULL,
                entity_type VARCHAR NOT NULL, -- referenced entity type
                entity_id UUID,      -- referenced entity id
                entity_name VARCHAR, -- if entity_type is user, this will be the user name
                active BOOLEAN NOT NULL DEFAULT TRUE,
                data JSONB NOT NULL DEFAULT '{}'::JSONB,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                creation_order SERIAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_activity_id ON activity_references(activity_id);
            CREATE INDEX IF NOT EXISTS idx_activity_entity_id ON activity_references(entity_id);
            CREATE INDEX IF NOT EXISTS idx_activity_reference_created_at
              ON activity_references(created_at);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_activity_reference_unique
              ON activity_references(activity_id, entity_id, entity_name, reference_type);

            CREATE TABLE IF NOT EXISTS entity_paths (
                entity_id UUID PRIMARY KEY,
                entity_type VARCHAR NOT NULL,
                path VARCHAR NOT NULL
            );
            CREATE INDEX IF NOT EXISTS entity_paths_path_idx
              ON entity_paths USING GIN (path public.gin_trgm_ops);

            CREATE OR REPLACE VIEW activity_feed AS
              SELECT
                ref.id as reference_id,
                ref.activity_id as activity_id,
                ref.reference_type as reference_type,

                -- what entity we're referencing
                ref.entity_type as entity_type,
                ref.entity_id as entity_id, -- for project level entities and other activities
                ref.entity_name as entity_name, -- for users
                ref_paths.path as entity_path, -- entity hierarchy position

                -- sorting stuff
                ref.created_at,
                ref.updated_at,
                ref.creation_order,

                -- actual activity
                act.activity_type as activity_type,
                act.body as body,
                act.data as activity_data,
                ref.data as reference_data,
                ref.active as active

              FROM
                activity_references as ref
              INNER JOIN
                activities as act ON ref.activity_id = act.id
              LEFT JOIN
                entity_paths as ref_paths ON ref.entity_id = ref_paths.entity_id;

            CREATE TABLE IF NOT EXISTS files (
              id UUID PRIMARY KEY,
              size BIGINT NOT NULL,
              author VARCHAR REFERENCES public.users(name) ON DELETE SET NULL ON UPDATE CASCADE,
              activity_id UUID REFERENCES activities(id) ON DELETE SET NULL,
              data JSONB NOT NULL DEFAULT '{}'::JSONB, -- contains mime, original file name etc
              created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
              updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_files_activity_id ON files(activity_id);

        END LOOP;
        RETURN;
   END;
   $$ LANGUAGE plpgsql;

SELECT create_activity_feed_in_projects();
DROP FUNCTION IF EXISTS create_activity_feed_in_projects();

----------------
-- AYON 1.3.1 --
----------------

-- Allow renaming users with developmnent bundle

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        JOIN pg_attribute a ON a.attnum = ANY (conkey) AND a.attrelid = conrelid
        JOIN pg_attribute af ON af.attnum = ANY (confkey) AND af.attrelid = confrelid
        WHERE confupdtype = 'c'
          AND contype = 'f'
          AND conrelid = 'public.bundles'::regclass
          AND a.attname = 'active_user'
    ) THEN
        -- Drop the existing foreign key constraint
        ALTER TABLE public.bundles
        DROP CONSTRAINT IF EXISTS bundles_active_user_fkey;

        -- Add a new foreign key constraint with ON UPDATE CASCADE
        ALTER TABLE public.bundles
        ADD CONSTRAINT bundles_active_user_fkey
        FOREIGN KEY (active_user)
        REFERENCES public.users(name)
        ON DELETE SET NULL
        ON UPDATE CASCADE;
    END IF;
END $$;

-- Allow renaming users with site settings

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        JOIN pg_attribute a ON a.attnum = ANY (conkey) AND a.attrelid = conrelid
        JOIN pg_attribute af ON af.attnum = ANY (confkey) AND af.attrelid = confrelid
        WHERE confupdtype = 'c'
          AND contype = 'f'
          AND conrelid = 'public.site_settings'::regclass
          AND a.attname = 'user_name'
    ) THEN
        -- Drop the existing foreign key constraint
        ALTER TABLE public.site_settings
        DROP CONSTRAINT IF EXISTS site_settings_user_name_fkey;

        -- Add a new foreign key constraint with ON UPDATE CASCADE
        ALTER TABLE public.site_settings
        ADD CONSTRAINT site_settings_user_name_fkey
        FOREIGN KEY (user_name)
        REFERENCES public.users(name)
        ON DELETE SET NULL
        ON UPDATE CASCADE;
    END IF;
END $$;

-- Allow renaming users with project.custom_roots and project.project_site_settings set

DO $$
DECLARE
    project_schema TEXT;
    table_name TEXT;
    column_name TEXT;
    constraint_name TEXT;
BEGIN
    FOR project_schema IN
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name LIKE 'project_%'
    LOOP
        FOR table_name, column_name, constraint_name IN
            SELECT
                tc.table_name,
                kcu.column_name,
                tc.constraint_name
            FROM
                information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
            WHERE
                tc.constraint_type = 'FOREIGN KEY'
                AND kcu.table_schema = project_schema
                AND kcu.column_name = 'user_name'
        LOOP
            -- Drop existing foreign key constraint
            EXECUTE format('
                ALTER TABLE %I.%I
                DROP CONSTRAINT %I;
            ', project_schema, table_name, constraint_name);

            -- Add new foreign key constraint with ON UPDATE CASCADE
            EXECUTE format('
                ALTER TABLE %I.%I
                ADD CONSTRAINT %I
                FOREIGN KEY (%I)
                REFERENCES public.users(name)
                ON DELETE CASCADE
                ON UPDATE CASCADE;
            ', project_schema, table_name, constraint_name, column_name);
        END LOOP;
    END LOOP;
END $$;


----------------
-- AYON 1.5 --
----------------

-- Add meta column to thumbnails
-- Remove files.author foreign key

CREATE OR REPLACE FUNCTION add_meta_column_to_thumbnails()
   RETURNS VOID  AS
   $$
   DECLARE rec RECORD;
   BEGIN
        FOR rec IN select distinct nspname from pg_namespace where nspname like 'project_%'
        LOOP
             EXECUTE
              'ALTER TABLE IF EXISTS ' || rec.nspname || '.thumbnails ' ||
              'ADD COLUMN IF NOT EXISTS meta JSONB DEFAULT ''{}''::JSONB ';

             EXECUTE
              'ALTER TABLE IF EXISTS ' || rec.nspname || '.files ' ||
              'DROP CONSTRAINT IF EXISTS files_author_fkey';
        END LOOP;
        RETURN;
   END;
   $$ LANGUAGE plpgsql;

SELECT add_meta_column_to_thumbnails();
DROP FUNCTION IF EXISTS add_meta_column_to_thumbnails();


----------------
-- AYON 1.5.3 --
----------------

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'events'
        AND table_schema = 'public'
        AND column_name = 'sender_type'
    ) THEN
        RAISE WARNING 'Adding sender_type column to events';
        ALTER TABLE IF EXISTS public.events
        ADD COLUMN sender_type VARCHAR;
    END IF;
END $$;


