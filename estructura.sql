CREATE TABLE
    IF NOT EXISTS "django_migrations" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "app" varchar(255) NOT NULL,
        "name" varchar(255) NOT NULL,
        "applied" datetime NOT NULL
    );

CREATE TABLE
    sqlite_sequence (name, seq);

CREATE TABLE
    IF NOT EXISTS "auth_group_permissions" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "group_id" integer NOT NULL REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED,
        "permission_id" integer NOT NULL REFERENCES "auth_permission" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE TABLE
    IF NOT EXISTS "auth_user_groups" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "group_id" integer NOT NULL REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE TABLE
    IF NOT EXISTS "auth_user_user_permissions" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "permission_id" integer NOT NULL REFERENCES "auth_permission" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE UNIQUE INDEX "auth_group_permissions_group_id_permission_id_0cd325b0_uniq" ON "auth_group_permissions" ("group_id", "permission_id");

CREATE INDEX "auth_group_permissions_group_id_b120cbf9" ON "auth_group_permissions" ("group_id");

CREATE INDEX "auth_group_permissions_permission_id_84c5c92e" ON "auth_group_permissions" ("permission_id");

CREATE UNIQUE INDEX "auth_user_groups_user_id_group_id_94350c0c_uniq" ON "auth_user_groups" ("user_id", "group_id");

CREATE INDEX "auth_user_groups_user_id_6a12ed8b" ON "auth_user_groups" ("user_id");

CREATE INDEX "auth_user_groups_group_id_97559544" ON "auth_user_groups" ("group_id");

CREATE UNIQUE INDEX "auth_user_user_permissions_user_id_permission_id_14a6b632_uniq" ON "auth_user_user_permissions" ("user_id", "permission_id");

CREATE INDEX "auth_user_user_permissions_user_id_a95ead1b" ON "auth_user_user_permissions" ("user_id");

CREATE INDEX "auth_user_user_permissions_permission_id_1fbb5f2c" ON "auth_user_user_permissions" ("permission_id");

CREATE TABLE
    IF NOT EXISTS "account_emailconfirmation" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "created" datetime NOT NULL,
        "sent" datetime NULL,
        "key" varchar(64) NOT NULL UNIQUE,
        "email_address_id" integer NOT NULL REFERENCES "account_emailaddress" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE INDEX "account_emailconfirmation_email_address_id_5b7f8c58" ON "account_emailconfirmation" ("email_address_id");

CREATE TABLE
    IF NOT EXISTS "account_emailaddress" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "verified" bool NOT NULL,
        "primary" bool NOT NULL,
        "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "email" varchar(254) NOT NULL
    );

CREATE UNIQUE INDEX "account_emailaddress_user_id_email_987c8728_uniq" ON "account_emailaddress" ("user_id", "email");

CREATE UNIQUE INDEX "unique_verified_email" ON "account_emailaddress" ("email")
WHERE
    "verified";

CREATE INDEX "account_emailaddress_user_id_2c513194" ON "account_emailaddress" ("user_id");

CREATE INDEX "account_emailaddress_email_03be32b2" ON "account_emailaddress" ("email");

CREATE UNIQUE INDEX "unique_primary_email" ON "account_emailaddress" ("user_id", "primary")
WHERE
    "primary";

CREATE TABLE
    IF NOT EXISTS "django_admin_log" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "object_id" text NULL,
        "object_repr" varchar(200) NOT NULL,
        "action_flag" smallint unsigned NOT NULL CHECK ("action_flag" >= 0),
        "change_message" text NOT NULL,
        "content_type_id" integer NULL REFERENCES "django_content_type" ("id") DEFERRABLE INITIALLY DEFERRED,
        "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "action_time" datetime NOT NULL
    );

CREATE INDEX "django_admin_log_content_type_id_c4bce8eb" ON "django_admin_log" ("content_type_id");

CREATE INDEX "django_admin_log_user_id_c564eba6" ON "django_admin_log" ("user_id");

CREATE TABLE
    IF NOT EXISTS "django_content_type" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "app_label" varchar(100) NOT NULL,
        "model" varchar(100) NOT NULL
    );

CREATE UNIQUE INDEX "django_content_type_app_label_model_76bd3d3b_uniq" ON "django_content_type" ("app_label", "model");

CREATE TABLE
    IF NOT EXISTS "auth_permission" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "content_type_id" integer NOT NULL REFERENCES "django_content_type" ("id") DEFERRABLE INITIALLY DEFERRED,
        "codename" varchar(100) NOT NULL,
        "name" varchar(255) NOT NULL
    );

CREATE UNIQUE INDEX "auth_permission_content_type_id_codename_01ab375a_uniq" ON "auth_permission" ("content_type_id", "codename");

CREATE INDEX "auth_permission_content_type_id_2f476e4b" ON "auth_permission" ("content_type_id");

CREATE TABLE
    IF NOT EXISTS "auth_group" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "name" varchar(150) NOT NULL UNIQUE
    );

CREATE TABLE
    IF NOT EXISTS "auth_user" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "password" varchar(128) NOT NULL,
        "last_login" datetime NULL,
        "is_superuser" bool NOT NULL,
        "username" varchar(150) NOT NULL UNIQUE,
        "last_name" varchar(150) NOT NULL,
        "email" varchar(254) NOT NULL,
        "is_staff" bool NOT NULL,
        "is_active" bool NOT NULL,
        "date_joined" datetime NOT NULL,
        "first_name" varchar(150) NOT NULL
    );

CREATE TABLE
    IF NOT EXISTS "django_session" (
        "session_key" varchar(40) NOT NULL PRIMARY KEY,
        "session_data" text NOT NULL,
        "expire_date" datetime NOT NULL
    );

CREATE INDEX "django_session_expire_date_a5c62663" ON "django_session" ("expire_date");

CREATE TABLE
    IF NOT EXISTS "django_site" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "name" varchar(50) NOT NULL,
        "domain" varchar(100) NOT NULL UNIQUE
    );

CREATE TABLE
    IF NOT EXISTS "socialaccount_socialapp_sites" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "socialapp_id" integer NOT NULL REFERENCES "socialaccount_socialapp" ("id") DEFERRABLE INITIALLY DEFERRED,
        "site_id" integer NOT NULL REFERENCES "django_site" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE UNIQUE INDEX "socialaccount_socialapp_sites_socialapp_id_site_id_71a9a768_uniq" ON "socialaccount_socialapp_sites" ("socialapp_id", "site_id");

CREATE INDEX "socialaccount_socialapp_sites_socialapp_id_97fb6e7d" ON "socialaccount_socialapp_sites" ("socialapp_id");

CREATE INDEX "socialaccount_socialapp_sites_site_id_2579dee5" ON "socialaccount_socialapp_sites" ("site_id");

CREATE TABLE
    IF NOT EXISTS "socialaccount_socialapp" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "provider" varchar(30) NOT NULL,
        "name" varchar(40) NOT NULL,
        "client_id" varchar(191) NOT NULL,
        "secret" varchar(191) NOT NULL,
        "key" varchar(191) NOT NULL,
        "provider_id" varchar(200) NOT NULL,
        "settings" text NOT NULL CHECK (
            (
                JSON_VALID ("settings")
                OR "settings" IS NULL
            )
        )
    );

CREATE TABLE
    IF NOT EXISTS "socialaccount_socialtoken" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "token" text NOT NULL,
        "token_secret" text NOT NULL,
        "expires_at" datetime NULL,
        "account_id" integer NOT NULL REFERENCES "socialaccount_socialaccount" ("id") DEFERRABLE INITIALLY DEFERRED,
        "app_id" integer NULL REFERENCES "socialaccount_socialapp" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE UNIQUE INDEX "socialaccount_socialtoken_app_id_account_id_fca4e0ac_uniq" ON "socialaccount_socialtoken" ("app_id", "account_id");

CREATE INDEX "socialaccount_socialtoken_account_id_951f210e" ON "socialaccount_socialtoken" ("account_id");

CREATE INDEX "socialaccount_socialtoken_app_id_636a42d7" ON "socialaccount_socialtoken" ("app_id");

CREATE TABLE
    IF NOT EXISTS "socialaccount_socialaccount" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "provider" varchar(200) NOT NULL,
        "uid" varchar(191) NOT NULL,
        "last_login" datetime NOT NULL,
        "date_joined" datetime NOT NULL,
        "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "extra_data" text NOT NULL CHECK (
            (
                JSON_VALID ("extra_data")
                OR "extra_data" IS NULL
            )
        )
    );

CREATE UNIQUE INDEX "socialaccount_socialaccount_provider_uid_fc810c6e_uniq" ON "socialaccount_socialaccount" ("provider", "uid");

CREATE INDEX "socialaccount_socialaccount_user_id_8146e70c" ON "socialaccount_socialaccount" ("user_id");

CREATE TABLE
    IF NOT EXISTS "documentacion_project" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "nombre" varchar(100) NOT NULL,
        "descripcion" text NOT NULL,
        "creado" datetime NOT NULL,
        "actualizado" datetime NOT NULL,
        "propietario_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE TABLE
    IF NOT EXISTS "documentacion_fase" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "nombre" varchar(100) NOT NULL,
        "proyecto_id" bigint NOT NULL REFERENCES "documentacion_project" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE TABLE
    IF NOT EXISTS "documentacion_subartefacto" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "nombre" varchar(100) NOT NULL,
        "enlace" varchar(200) NOT NULL,
        "fase_id" bigint NOT NULL REFERENCES "documentacion_fase" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE TABLE
    IF NOT EXISTS "documentacion_artefacto" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "tipo" varchar(4) NOT NULL,
        "titulo" varchar(100) NOT NULL,
        "contenido" text NOT NULL,
        "generado_por_ia" bool NOT NULL,
        "creado" datetime NOT NULL,
        "actualizado" datetime NOT NULL,
        "fase_id" bigint NOT NULL REFERENCES "documentacion_fase" ("id") DEFERRABLE INITIALLY DEFERRED,
        "proyecto_id" bigint NOT NULL REFERENCES "documentacion_project" ("id") DEFERRABLE INITIALLY DEFERRED,
        "subartefacto_id" bigint NULL REFERENCES "documentacion_subartefacto" ("id") DEFERRABLE INITIALLY DEFERRED,
        "contexto" text NULL
    );

CREATE INDEX "documentacion_project_propietario_id_b339ba59" ON "documentacion_project" ("propietario_id");

CREATE UNIQUE INDEX "documentacion_fase_proyecto_id_nombre_2515459a_uniq" ON "documentacion_fase" ("proyecto_id", "nombre");

CREATE INDEX "documentacion_fase_proyecto_id_0fd0d056" ON "documentacion_fase" ("proyecto_id");

CREATE UNIQUE INDEX "documentacion_subartefacto_fase_id_nombre_ab33e65f_uniq" ON "documentacion_subartefacto" ("fase_id", "nombre");

CREATE INDEX "documentacion_subartefacto_fase_id_50f4b5d7" ON "documentacion_subartefacto" ("fase_id");

CREATE INDEX "documentacion_artefacto_fase_id_108acb8d" ON "documentacion_artefacto" ("fase_id");

CREATE INDEX "documentacion_artefacto_proyecto_id_ea9af978" ON "documentacion_artefacto" ("proyecto_id");

CREATE INDEX "documentacion_artefacto_subartefacto_id_f2b6b52d" ON "documentacion_artefacto" ("subartefacto_id");