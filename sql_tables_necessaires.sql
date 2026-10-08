-- Script SQL Server avec uniquement les tables nécessaires pour le projet
-- Focus principal : utilisateurs, contacts, campagnes, forfaits, tickets support

BEGIN TRY
    BEGIN TRANSACTION;

    -- ============================================================
    -- 1) Utilisateurs / auth
    -- ============================================================

    IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'users_department')
    BEGIN
        CREATE TABLE dbo.users_department (
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(120) NOT NULL UNIQUE
        );
    END;

    IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'users_user')
    BEGIN
        CREATE TABLE dbo.users_user (
            id INT IDENTITY(1,1) PRIMARY KEY,
            password NVARCHAR(128) NOT NULL,
            last_login DATETIME2 NULL,
            is_superuser BIT NOT NULL DEFAULT 0,
            username NVARCHAR(150) NOT NULL UNIQUE,
            first_name NVARCHAR(150) NOT NULL DEFAULT '',
            last_name NVARCHAR(150) NOT NULL DEFAULT '',
            email NVARCHAR(254) NOT NULL DEFAULT '',
            is_staff BIT NOT NULL DEFAULT 0,
            is_active BIT NOT NULL DEFAULT 1,
            date_joined DATETIME2 NOT NULL,
            role NVARCHAR(20) NOT NULL DEFAULT 'client',
            phone NVARCHAR(20) NULL,
            company_name NVARCHAR(255) NULL,
            company_address NVARCHAR(255) NULL,
            birth_date DATE NULL,
            civility NVARCHAR(20) NULL,
            activity_sector NVARCHAR(120) NULL,
            locality NVARCHAR(120) NULL,
            arrondissement NVARCHAR(120) NULL,
            low_balance_alerts BIT NOT NULL DEFAULT 0,
            created_at DATETIME2 NOT NULL DEFAULT GETDATE()
        );
    END;

    IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'users_userapitoken')
    BEGIN
        CREATE TABLE dbo.users_userapitoken (
            id INT IDENTITY(1,1) PRIMARY KEY,
            user_id INT NOT NULL UNIQUE,
            [key] NVARCHAR(64) NOT NULL UNIQUE,
            created_at DATETIME2 NOT NULL DEFAULT GETDATE()
        );
    END;

    IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'users_smtpconfiguration')
    BEGIN
        CREATE TABLE dbo.users_smtpconfiguration (
            id INT IDENTITY(1,1) PRIMARY KEY,
            user_id INT NOT NULL UNIQUE,
            provider NVARCHAR(30) NOT NULL DEFAULT 'custom',
            host NVARCHAR(255) NOT NULL,
            port INT NOT NULL DEFAULT 587,
            username NVARCHAR(255) NOT NULL,
            from_email NVARCHAR(254) NOT NULL,
            security NVARCHAR(10) NOT NULL DEFAULT 'tls',
            encrypted_password NVARCHAR(MAX) NOT NULL DEFAULT '',
            signature NVARCHAR(MAX) NOT NULL DEFAULT '',
            updated_at DATETIME2 NOT NULL DEFAULT GETDATE()
        );
    END;

    -- Mise à niveau des bases déjà initialisées avant l'ajout des alertes de solde.
    IF NOT EXISTS (
        SELECT 1 FROM sys.columns
        WHERE object_id = OBJECT_ID(N'dbo.users_user') AND name = N'low_balance_alerts'
    )
    BEGIN
        ALTER TABLE dbo.users_user
        ADD low_balance_alerts BIT NOT NULL CONSTRAINT df_users_user_low_balance_alerts DEFAULT 0;
    END;

    IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'users_otpcode')
    BEGIN
        CREATE TABLE dbo.users_otpcode (
            id INT IDENTITY(1,1) PRIMARY KEY,
            phone NVARCHAR(20) NOT NULL,
            code NVARCHAR(6) NOT NULL,
            purpose NVARCHAR(20) NOT NULL DEFAULT 'registration',
            created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
            expires_at DATETIME2 NOT NULL,
            verified BIT NOT NULL DEFAULT 0
        );
    END;

    IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'users_arrondissement')
    BEGIN
        CREATE TABLE dbo.users_arrondissement (
            id INT IDENTITY(1,1) PRIMARY KEY,
            department_id INT NOT NULL,
            name NVARCHAR(120) NOT NULL,
            CONSTRAINT fk_users_arrondissement_department FOREIGN KEY (department_id) REFERENCES dbo.users_department(id) ON DELETE CASCADE,
            CONSTRAINT uq_users_arrondissement_department_name UNIQUE (department_id, name)
        );
    END;

    -- ============================================================
    -- 2) Contacts
    -- ============================================================

    IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'contacts_contact')
    BEGIN
        CREATE TABLE dbo.contacts_contact (
            id INT IDENTITY(1,1) PRIMARY KEY,
            user_id INT NOT NULL,
            name NVARCHAR(255) NOT NULL,
            phone NVARCHAR(20) NOT NULL,
            email NVARCHAR(254) NULL,
            tags NVARCHAR(MAX) NOT NULL DEFAULT '[]',
            created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
            CONSTRAINT fk_contacts_contact_user FOREIGN KEY (user_id) REFERENCES dbo.users_user(id) ON DELETE CASCADE
        );
    END;

    IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'contacts_contactgroup')
    BEGIN
        CREATE TABLE dbo.contacts_contactgroup (
            id INT IDENTITY(1,1) PRIMARY KEY,
            user_id INT NOT NULL,
            name NVARCHAR(255) NOT NULL,
            description NVARCHAR(MAX) NULL,
            created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
            CONSTRAINT fk_contacts_contactgroup_user FOREIGN KEY (user_id) REFERENCES dbo.users_user(id) ON DELETE CASCADE
        );
    END;

    IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'contacts_contactgroupmember')
    BEGIN
        CREATE TABLE dbo.contacts_contactgroupmember (
            id INT IDENTITY(1,1) PRIMARY KEY,
            group_id INT NOT NULL,
            contact_id INT NOT NULL,
            CONSTRAINT fk_contacts_contactgroupmember_group FOREIGN KEY (group_id) REFERENCES dbo.contacts_contactgroup(id) ON DELETE CASCADE,
            CONSTRAINT fk_contacts_contactgroupmember_contact FOREIGN KEY (contact_id) REFERENCES dbo.contacts_contact(id) ON DELETE NO ACTION,
            CONSTRAINT uq_contacts_contactgroupmember UNIQUE (group_id, contact_id)
        );
    END;

    -- ============================================================
    -- 3) Campagnes / SMS
    -- ============================================================

    IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'campaigns_campaign')
    BEGIN
        CREATE TABLE dbo.campaigns_campaign (
            id INT IDENTITY(1,1) PRIMARY KEY,
            user_id INT NOT NULL,
            title NVARCHAR(255) NOT NULL,
            message NVARCHAR(MAX) NOT NULL,
            scheduled_at DATETIME2 NULL,
            status NVARCHAR(20) NOT NULL DEFAULT 'draft',
            created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
            CONSTRAINT fk_campaigns_campaign_user FOREIGN KEY (user_id) REFERENCES dbo.users_user(id) ON DELETE CASCADE
        );
    END;

    IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'campaigns_campaignrecipient')
    BEGIN
        CREATE TABLE dbo.campaigns_campaignrecipient (
            id INT IDENTITY(1,1) PRIMARY KEY,
            campaign_id INT NOT NULL,
            contact_id INT NOT NULL,
            status NVARCHAR(20) NOT NULL DEFAULT 'pending',
            sent_at DATETIME2 NULL,
            CONSTRAINT fk_campaigns_campaignrecipient_campaign FOREIGN KEY (campaign_id) REFERENCES dbo.campaigns_campaign(id) ON DELETE CASCADE,
            CONSTRAINT fk_campaigns_campaignrecipient_contact FOREIGN KEY (contact_id) REFERENCES dbo.contacts_contact(id) ON DELETE NO ACTION,
            CONSTRAINT uq_campaigns_campaignrecipient UNIQUE (campaign_id, contact_id)
        );
    END;

    IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'campaigns_smslog')
    BEGIN
        CREATE TABLE dbo.campaigns_smslog (
            id INT IDENTITY(1,1) PRIMARY KEY,
            campaign_id INT NULL,
            recipient_id INT NULL,
            provider NVARCHAR(50) NOT NULL DEFAULT 'twilio',
            status NVARCHAR(20) NOT NULL DEFAULT 'pending',
            response_code NVARCHAR(50) NULL,
            sent_at DATETIME2 NOT NULL DEFAULT GETDATE(),
            CONSTRAINT fk_campaigns_smslog_campaign FOREIGN KEY (campaign_id) REFERENCES dbo.campaigns_campaign(id) ON DELETE SET NULL,
            CONSTRAINT fk_campaigns_smslog_recipient FOREIGN KEY (recipient_id) REFERENCES dbo.contacts_contact(id) ON DELETE NO ACTION
        );
    END;

    -- ============================================================
    -- 4) Forfaits / paiements
    -- ============================================================

    IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'billing_smspackage')
    BEGIN
        CREATE TABLE dbo.billing_smspackage (
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(255) NOT NULL,
            quantity INT NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            is_active BIT NOT NULL DEFAULT 1,
            created_at DATETIME2 NOT NULL DEFAULT GETDATE()
        );
    END;

    IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'billing_transaction')
    BEGIN
        CREATE TABLE dbo.billing_transaction (
            id INT IDENTITY(1,1) PRIMARY KEY,
            user_id INT NOT NULL,
            package_id INT NULL,
            amount DECIMAL(10,2) NOT NULL,
            payment_method NVARCHAR(50) NOT NULL DEFAULT 'card',
            status NVARCHAR(20) NOT NULL DEFAULT 'pending',
            created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
            CONSTRAINT fk_billing_transaction_user FOREIGN KEY (user_id) REFERENCES dbo.users_user(id) ON DELETE CASCADE,
            CONSTRAINT fk_billing_transaction_package FOREIGN KEY (package_id) REFERENCES dbo.billing_smspackage(id) ON DELETE SET NULL
        );
    END;

    -- ============================================================
    -- 5) Support client
    -- ============================================================

    IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'support_supportticket')
    BEGIN
        CREATE TABLE dbo.support_supportticket (
            id INT IDENTITY(1,1) PRIMARY KEY,
            user_id INT NOT NULL,
            subject NVARCHAR(255) NOT NULL,
            message NVARCHAR(MAX) NOT NULL,
            status NVARCHAR(20) NOT NULL DEFAULT 'open',
            created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
            CONSTRAINT fk_support_supportticket_user FOREIGN KEY (user_id) REFERENCES dbo.users_user(id) ON DELETE CASCADE
        );
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
    DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
    DECLARE @ErrorState INT = ERROR_STATE();

    RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
END CATCH;
GO

SELECT TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME;
