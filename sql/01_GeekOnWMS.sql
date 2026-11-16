/* [AD] 16/11/2026 GeekOn WMS: δημιουργία βάσης GeekOnWMS (φάση 1)
   Τρέχει ο Άκης στο SSMS, συνδεδεμένος σαν διαχειριστής του SQL Server.
   ΠΡΙΝ το τρέξεις: άλλαξε το <<ΚΩΔΙΚΟΣ_WMS>> (ενότητα 12) με δυνατό κωδικό και κράτα τον. Ο κωδικός ΔΕΝ ανεβαίνει στο GitHub.
   Δεν αγγίζει τη βάση GEEKON (SoftOne) ούτε την LV_GEEKON (Mantis).
   Αρχές: ΤΙΠΟΤΑ δεν σβήνεται. Κινήσεις = μόνο προσθήκη (λάθος → αντίθετη κίνηση).
          Ρυθμίσεις (όροφοι, Dexion, θέσεις, χρήστες, είδη) κρατάνε αυτόματα όλο το ιστορικό τους (temporal tables). */

-- ============================================================ 1. Βάση
IF DB_ID(N'GeekOnWMS') IS NULL CREATE DATABASE GeekOnWMS;
GO
ALTER DATABASE GeekOnWMS SET RECOVERY SIMPLE;
GO
USE GeekOnWMS;
GO
IF OBJECT_ID(N'wms.Movement') IS NOT NULL
BEGIN RAISERROR(N'[WMS] Η βάση GeekOnWMS έχει ήδη φτιαχτεί. Δεν κάνω τίποτα.', 16, 1); SET NOEXEC ON; END;
GO
IF SCHEMA_ID(N'wms') IS NULL EXEC(N'CREATE SCHEMA wms');
GO

-- ============================================================ 2. Ζώνες (εσωτερικές αποθήκες WMS)
CREATE TABLE wms.Zone (
  ZoneCode     varchar(10)   NOT NULL CONSTRAINT PK_Zone PRIMARY KEY,
  Name         nvarchar(60)  NOT NULL,
  CountsInS1   bit           NOT NULL CONSTRAINT DF_Zone_CountsInS1 DEFAULT (1),   -- μετράει στο απόθεμα SoftOne
  Sellable     bit           NOT NULL CONSTRAINT DF_Zone_Sellable   DEFAULT (0),   -- πουλιέται / picking
  Active       bit           NOT NULL CONSTRAINT DF_Zone_Active     DEFAULT (1),
  ChangedBy    nvarchar(50)  NOT NULL CONSTRAINT DF_Zone_ChangedBy  DEFAULT (N'system'),
  ValidFrom    datetime2(3)  GENERATED ALWAYS AS ROW START HIDDEN NOT NULL,
  ValidTo      datetime2(3)  GENERATED ALWAYS AS ROW END   HIDDEN NOT NULL,
  PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = wms.Zone_History));
GO

-- ============================================================ 3. Χωροταξία: Όροφος → Dexion → Θέση
CREATE TABLE wms.Floor (
  FloorId      int IDENTITY(1,1) NOT NULL CONSTRAINT PK_Floor PRIMARY KEY,
  Code         varchar(3)    NOT NULL CONSTRAINT UQ_Floor_Code UNIQUE,              -- IS, YP, O1
  Name         nvarchar(60)  NOT NULL,
  Lvl          smallint      NOT NULL CONSTRAINT DF_Floor_Lvl DEFAULT (0),          -- 0 ισόγειο, -1 υπόγειο, 1 πρώτος
  Speed        varchar(6)    NOT NULL CONSTRAINT CK_Floor_Speed CHECK (Speed IN ('FAST','SLOW','STATIC')),
  WidthM       decimal(6,2)  NULL,
  DepthM       decimal(6,2)  NULL,
  ShapeJson    nvarchar(max) NULL,          -- γωνίες τοίχων από το 3D [[x,z],...] σε μέτρα
  WallsJson    nvarchar(max) NULL,          -- εσωτερικοί τοίχοι
  PlanImage    nvarchar(260) NULL,          -- αρχείο εικόνας κάτοψης στον server (όχι μέσα στη βάση)
  Active       bit           NOT NULL CONSTRAINT DF_Floor_Active    DEFAULT (1),
  ChangedBy    nvarchar(50)  NOT NULL CONSTRAINT DF_Floor_ChangedBy DEFAULT (N'system'),
  ValidFrom    datetime2(3)  GENERATED ALWAYS AS ROW START HIDDEN NOT NULL,
  ValidTo      datetime2(3)  GENERATED ALWAYS AS ROW END   HIDDEN NOT NULL,
  PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = wms.Floor_History));
GO

CREATE TABLE wms.Rack (                     -- ένα Dexion
  RackId       int IDENTITY(1,1) NOT NULL CONSTRAINT PK_Rack PRIMARY KEY,
  FloorId      int           NOT NULL CONSTRAINT FK_Rack_Floor REFERENCES wms.Floor(FloorId),
  Aisle        smallint      NOT NULL CONSTRAINT CK_Rack_Aisle CHECK (Aisle BETWEEN 1 AND 99),
  Num          smallint      NOT NULL CONSTRAINT CK_Rack_Num   CHECK (Num   BETWEEN 1 AND 99),
  X            decimal(6,2)  NOT NULL CONSTRAINT DF_Rack_X DEFAULT (0),   -- θέση στο 3D (μέτρα)
  Z            decimal(6,2)  NOT NULL CONSTRAINT DF_Rack_Z DEFAULT (0),
  Rot          smallint      NOT NULL CONSTRAINT CK_Rack_Rot CHECK (Rot IN (0,90,180,270)),
  WidthCm      smallint      NOT NULL CONSTRAINT DF_Rack_W DEFAULT (100),
  DepthCm      smallint      NOT NULL CONSTRAINT DF_Rack_D DEFAULT (40),
  HeightCm     smallint      NOT NULL CONSTRAINT DF_Rack_H DEFAULT (200),
  ShelvesJson  nvarchar(400) NOT NULL,      -- θέσεις ανά ράφι από κάτω προς τα πάνω, π.χ. [6,10,12,12,12]
  Active       bit           NOT NULL CONSTRAINT DF_Rack_Active    DEFAULT (1),
  ChangedBy    nvarchar(50)  NOT NULL CONSTRAINT DF_Rack_ChangedBy DEFAULT (N'system'),
  ValidFrom    datetime2(3)  GENERATED ALWAYS AS ROW START HIDDEN NOT NULL,
  ValidTo      datetime2(3)  GENERATED ALWAYS AS ROW END   HIDDEN NOT NULL,
  PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = wms.Rack_History));
GO
-- ίδιος κωδικός Dexion μόνο μία φορά ανά όροφο (στα ενεργά)
CREATE UNIQUE INDEX UX_Rack_Code ON wms.Rack (FloorId, Aisle, Num) WHERE Active = 1;
GO

CREATE TABLE wms.Location (                 -- θέση: IS-A02-D03-R01-P12 (ή θέση ζώνης χωρίς Dexion, π.χ. IS-FAULTY)
  LocId        int IDENTITY(1,1) NOT NULL CONSTRAINT PK_Location PRIMARY KEY,
  Code         varchar(30)   NOT NULL,
  FloorId      int           NOT NULL CONSTRAINT FK_Loc_Floor REFERENCES wms.Floor(FloorId),
  RackId       int           NULL     CONSTRAINT FK_Loc_Rack  REFERENCES wms.Rack(RackId),
  ShelfNo      tinyint       NULL,      -- R01 = κάτω ράφι
  PosNo        tinyint       NULL,      -- P01 = αριστερή θέση από μπροστά
  ZoneCode     varchar(10)   NOT NULL CONSTRAINT DF_Loc_Zone DEFAULT ('MAIN') CONSTRAINT FK_Loc_Zone REFERENCES wms.Zone(ZoneCode),
  CapacityPcs  int           NULL,      -- χωρητικότητα σε τεμάχια (αν τη θέλουμε)
  Active       bit           NOT NULL CONSTRAINT DF_Loc_Active    DEFAULT (1),
  ChangedBy    nvarchar(50)  NOT NULL CONSTRAINT DF_Loc_ChangedBy DEFAULT (N'system'),
  ValidFrom    datetime2(3)  GENERATED ALWAYS AS ROW START HIDDEN NOT NULL,
  ValidTo      datetime2(3)  GENERATED ALWAYS AS ROW END   HIDDEN NOT NULL,
  PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = wms.Location_History));
GO
CREATE UNIQUE INDEX UX_Location_Code ON wms.Location (Code);   -- ο κωδικός δεν ξαναχρησιμοποιείται ποτέ (ετικέτες!)
CREATE INDEX IX_Location_Rack ON wms.Location (RackId);
GO

-- ============================================================ 4. Είδη (έρχονται ΜΟΝΟ από το SoftOne)
CREATE TABLE wms.Item (
  Mtrl         int           NOT NULL CONSTRAINT PK_Item PRIMARY KEY,   -- MTRL.MTRL του SoftOne
  Code         nvarchar(50)  NOT NULL,
  Name         nvarchar(255) NULL,
  Active       bit           NOT NULL CONSTRAINT DF_Item_Active DEFAULT (1),
  S1UpdDate    datetime      NULL,      -- MTRL.UPDDATE την ώρα του συγχρονισμού
  ChangedBy    nvarchar(50)  NOT NULL CONSTRAINT DF_Item_ChangedBy DEFAULT (N'sync'),
  ValidFrom    datetime2(3)  GENERATED ALWAYS AS ROW START HIDDEN NOT NULL,
  ValidTo      datetime2(3)  GENERATED ALWAYS AS ROW END   HIDDEN NOT NULL,
  PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = wms.Item_History));
GO
CREATE INDEX IX_Item_Code ON wms.Item (Code);
GO

CREATE TABLE wms.ItemCode (                 -- όλοι οι κωδικοί που σκανάρονται για ένα είδος
  ItemCodeId   int IDENTITY(1,1) NOT NULL CONSTRAINT PK_ItemCode PRIMARY KEY,
  Mtrl         int           NOT NULL CONSTRAINT FK_ItemCode_Item REFERENCES wms.Item(Mtrl),
  Code         nvarchar(60)  NOT NULL,
  Kind         varchar(8)    NOT NULL CONSTRAINT CK_ItemCode_Kind CHECK (Kind IN ('CODE1','CODE2','SUPP','BARCODE')),
  Supplier     int           NULL,      -- TRDR προμηθευτή όταν Kind = SUPP
  Active       bit           NOT NULL CONSTRAINT DF_ItemCode_Active DEFAULT (1),
  ChangedBy    nvarchar(50)  NOT NULL CONSTRAINT DF_ItemCode_ChangedBy DEFAULT (N'sync'),
  ValidFrom    datetime2(3)  GENERATED ALWAYS AS ROW START HIDDEN NOT NULL,
  ValidTo      datetime2(3)  GENERATED ALWAYS AS ROW END   HIDDEN NOT NULL,
  PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = wms.ItemCode_History));
GO
CREATE INDEX IX_ItemCode_Code ON wms.ItemCode (Code) INCLUDE (Mtrl, Active);
CREATE INDEX IX_ItemCode_Mtrl ON wms.ItemCode (Mtrl);
GO

-- ============================================================ 5. Χρήστες
CREATE TABLE wms.AppUser (
  UserId       int IDENTITY(1,1) NOT NULL CONSTRAINT PK_AppUser PRIMARY KEY,
  UserName     nvarchar(50)  NOT NULL CONSTRAINT UQ_AppUser_UserName UNIQUE,
  FullName     nvarchar(100) NOT NULL,
  Role         varchar(8)    NOT NULL CONSTRAINT CK_AppUser_Role CHECK (Role IN ('ADMIN','MANAGER','PICKER','VIEW')),
  PwdHash      varchar(200)  NULL,      -- scrypt από τον server, ΠΟΤΕ καθαρός κωδικός
  PinHash      varchar(200)  NULL,      -- PIN για το PDA (hash)
  TotpOn       bit           NOT NULL CONSTRAINT DF_AppUser_TotpOn DEFAULT (0),   -- Authenticator (για διαχειριστές)
  Lang         char(2)       NOT NULL CONSTRAINT DF_AppUser_Lang   DEFAULT ('el'),
  Active       bit           NOT NULL CONSTRAINT DF_AppUser_Active DEFAULT (1),
  ChangedBy    nvarchar(50)  NOT NULL CONSTRAINT DF_AppUser_ChangedBy DEFAULT (N'system'),
  ValidFrom    datetime2(3)  GENERATED ALWAYS AS ROW START HIDDEN NOT NULL,
  ValidTo      datetime2(3)  GENERATED ALWAYS AS ROW END   HIDDEN NOT NULL,
  PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = wms.AppUser_History));
GO

CREATE TABLE wms.LoginLog (                 -- κάθε προσπάθεια εισόδου, μόνο προσθήκη
  LoginId      bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_LoginLog PRIMARY KEY,
  At           datetime2(3)  NOT NULL CONSTRAINT DF_LoginLog_At DEFAULT (SYSDATETIME()),
  UserName     nvarchar(50)  NOT NULL,
  UserId       int           NULL CONSTRAINT FK_LoginLog_User REFERENCES wms.AppUser(UserId),
  Ok           bit           NOT NULL,
  Device       nvarchar(60)  NULL,      -- PDA-1, PC Άκη κλπ
  Ip           varchar(45)   NULL,
  Note         nvarchar(200) NULL
);
GO

-- ============================================================ 6. Θέσεις picking (IS) με ελάχιστο / μέγιστο
CREATE TABLE wms.PickFace (
  PickFaceId   int IDENTITY(1,1) NOT NULL CONSTRAINT PK_PickFace PRIMARY KEY,
  Mtrl         int           NOT NULL CONSTRAINT FK_PickFace_Item REFERENCES wms.Item(Mtrl),
  LocId        int           NOT NULL CONSTRAINT FK_PickFace_Loc  REFERENCES wms.Location(LocId),
  MinQty       int           NOT NULL CONSTRAINT CK_PickFace_Min CHECK (MinQty >= 0),
  MaxQty       int           NOT NULL,
  Locked       bit           NOT NULL CONSTRAINT DF_PickFace_Locked DEFAULT (0),   -- 1 = τα όρισε ο Άκης, δεν τα αλλάζει ο υπολογισμός
  Active       bit           NOT NULL CONSTRAINT DF_PickFace_Active DEFAULT (1),
  ChangedBy    nvarchar(50)  NOT NULL CONSTRAINT DF_PickFace_ChangedBy DEFAULT (N'system'),
  ValidFrom    datetime2(3)  GENERATED ALWAYS AS ROW START HIDDEN NOT NULL,
  ValidTo      datetime2(3)  GENERATED ALWAYS AS ROW END   HIDDEN NOT NULL,
  PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo),
  CONSTRAINT CK_PickFace_MinMax CHECK (MaxQty >= MinQty)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = wms.PickFace_History));
GO
CREATE UNIQUE INDEX UX_PickFace ON wms.PickFace (Mtrl, LocId) WHERE Active = 1;
GO

-- ============================================================ 7. Ρυθμίσεις
CREATE TABLE wms.Setting (
  SKey         varchar(50)   NOT NULL CONSTRAINT PK_Setting PRIMARY KEY,
  SValue       nvarchar(400) NOT NULL,
  Note         nvarchar(200) NULL,
  ChangedBy    nvarchar(50)  NOT NULL CONSTRAINT DF_Setting_ChangedBy DEFAULT (N'system'),
  ValidFrom    datetime2(3)  GENERATED ALWAYS AS ROW START HIDDEN NOT NULL,
  ValidTo      datetime2(3)  GENERATED ALWAYS AS ROW END   HIDDEN NOT NULL,
  PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = wms.Setting_History));
GO

-- ============================================================ 8. ΚΙΝΗΣΕΙΣ: η καρδιά της ιχνηλασιμότητας (μόνο προσθήκη)
-- Από θέση = NULL → ήρθε απ' έξω (παραλαβή, επιστροφή πελάτη, + απογραφής)
-- Σε θέση  = NULL → έφυγε από την εταιρεία (αποστολή, επιστροφή σε προμηθευτή, − απογραφής, καταστροφή)
CREATE TABLE wms.Movement (
  MoveId       bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_Movement PRIMARY KEY,
  At           datetime2(3)  NOT NULL CONSTRAINT DF_Move_At DEFAULT (SYSDATETIME()),
  UserId       int           NOT NULL CONSTRAINT FK_Move_User REFERENCES wms.AppUser(UserId),
  Device       nvarchar(60)  NULL,
  MoveType     varchar(6)    NOT NULL CONSTRAINT CK_Move_Type CHECK (MoveType IN
                 ('RCV','PUT','MOV','RPL','PICK','SHIP','INV','RET','RTS','SCRAP','REV')),
  Mtrl         int           NOT NULL CONSTRAINT FK_Move_Item REFERENCES wms.Item(Mtrl),
  Qty          int           NOT NULL CONSTRAINT CK_Move_Qty CHECK (Qty > 0),
  FromLocId    int           NULL CONSTRAINT FK_Move_From REFERENCES wms.Location(LocId),
  ToLocId      int           NULL CONSTRAINT FK_Move_To   REFERENCES wms.Location(LocId),
  S1Findoc     int           NULL,      -- παραστατικό SoftOne (FINDOC), αν υπάρχει
  DocRef       nvarchar(60)  NULL,      -- π.χ. ΠΣΚ0000123, παραγγελία
  Scanned      nvarchar(100) NULL,      -- τι σκανάρισε ακριβώς
  Reason       nvarchar(200) NULL,
  ReversesId   bigint        NULL CONSTRAINT FK_Move_Rev REFERENCES wms.Movement(MoveId),   -- διόρθωση λάθους
  CONSTRAINT CK_Move_FromTo CHECK (FromLocId IS NOT NULL OR ToLocId IS NOT NULL),
  CONSTRAINT CK_Move_NotSame CHECK (FromLocId IS NULL OR ToLocId IS NULL OR FromLocId <> ToLocId)
);
GO
CREATE INDEX IX_Move_Mtrl ON wms.Movement (Mtrl, At);
CREATE INDEX IX_Move_To   ON wms.Movement (ToLocId)   INCLUDE (Mtrl, Qty) WHERE ToLocId   IS NOT NULL;
CREATE INDEX IX_Move_From ON wms.Movement (FromLocId) INCLUDE (Mtrl, Qty) WHERE FromLocId IS NOT NULL;
CREATE INDEX IX_Move_At   ON wms.Movement (At);
GO

-- ============================================================ 9. Κλείδωμα: τίποτα δεν σβήνεται / δεν αλλάζει στις κινήσεις
CREATE TRIGGER wms.trg_Movement_Lock ON wms.Movement INSTEAD OF UPDATE, DELETE AS
BEGIN SET NOCOUNT ON; THROW 50001, N'[WMS] Οι κινήσεις δεν αλλάζουν και δεν σβήνονται. Για διόρθωση κάνε αντίθετη κίνηση (REV).', 1; END;
GO
CREATE TRIGGER wms.trg_LoginLog_Lock ON wms.LoginLog INSTEAD OF UPDATE, DELETE AS
BEGIN SET NOCOUNT ON; THROW 50002, N'[WMS] Το ιστορικό εισόδων δεν αλλάζει και δεν σβήνεται.', 1; END;
GO
-- ρυθμίσεις: αλλάζουν (κρατιέται ιστορικό), αλλά ΔΕΝ σβήνονται → Active = 0
CREATE TRIGGER wms.trg_Zone_NoDelete     ON wms.Zone     AFTER DELETE AS BEGIN SET NOCOUNT ON; THROW 50010, N'[WMS] Δεν σβήνεται: βάλε Active = 0.', 1; END;
GO
CREATE TRIGGER wms.trg_Floor_NoDelete    ON wms.Floor    AFTER DELETE AS BEGIN SET NOCOUNT ON; THROW 50010, N'[WMS] Δεν σβήνεται: βάλε Active = 0.', 1; END;
GO
CREATE TRIGGER wms.trg_Rack_NoDelete     ON wms.Rack     AFTER DELETE AS BEGIN SET NOCOUNT ON; THROW 50010, N'[WMS] Δεν σβήνεται: βάλε Active = 0.', 1; END;
GO
CREATE TRIGGER wms.trg_Location_NoDelete ON wms.Location AFTER DELETE AS BEGIN SET NOCOUNT ON; THROW 50010, N'[WMS] Δεν σβήνεται: βάλε Active = 0.', 1; END;
GO
CREATE TRIGGER wms.trg_Item_NoDelete     ON wms.Item     AFTER DELETE AS BEGIN SET NOCOUNT ON; THROW 50010, N'[WMS] Δεν σβήνεται: βάλε Active = 0.', 1; END;
GO
CREATE TRIGGER wms.trg_ItemCode_NoDelete ON wms.ItemCode AFTER DELETE AS BEGIN SET NOCOUNT ON; THROW 50010, N'[WMS] Δεν σβήνεται: βάλε Active = 0.', 1; END;
GO
CREATE TRIGGER wms.trg_AppUser_NoDelete  ON wms.AppUser  AFTER DELETE AS BEGIN SET NOCOUNT ON; THROW 50010, N'[WMS] Δεν σβήνεται: βάλε Active = 0.', 1; END;
GO
CREATE TRIGGER wms.trg_PickFace_NoDelete ON wms.PickFace AFTER DELETE AS BEGIN SET NOCOUNT ON; THROW 50010, N'[WMS] Δεν σβήνεται: βάλε Active = 0.', 1; END;
GO
CREATE TRIGGER wms.trg_Setting_NoDelete  ON wms.Setting  AFTER DELETE AS BEGIN SET NOCOUNT ON; THROW 50010, N'[WMS] Δεν σβήνεται.', 1; END;
GO
-- η θέση δεν αλλάζει κωδικό όταν έχει κινήσεις (οι ετικέτες είναι τυπωμένες)
CREATE TRIGGER wms.trg_Location_CodeLock ON wms.Location AFTER UPDATE AS
BEGIN
  SET NOCOUNT ON;
  IF UPDATE(Code) AND EXISTS (SELECT 1 FROM inserted i JOIN deleted d ON d.LocId = i.LocId
                              WHERE i.Code <> d.Code
                                AND EXISTS (SELECT 1 FROM wms.Movement m WHERE m.FromLocId = i.LocId OR m.ToLocId = i.LocId))
    THROW 50011, N'[WMS] Η θέση έχει κινήσεις: δεν αλλάζει κωδικός. Φτιάξε νέα θέση.', 1;
END;
GO

-- ============================================================ 10. Απόθεμα = άθροισμα κινήσεων
CREATE VIEW wms.vStock AS                  -- τεμάχια ανά θέση και είδος (τώρα)
SELECT s.LocId, l.Code AS LocCode, l.ZoneCode, s.Mtrl, i.Code AS ItemCode, SUM(s.Q) AS Qty
FROM (SELECT ToLocId AS LocId, Mtrl, Qty AS Q FROM wms.Movement WHERE ToLocId IS NOT NULL
      UNION ALL
      SELECT FromLocId, Mtrl, -Qty FROM wms.Movement WHERE FromLocId IS NOT NULL) s
JOIN wms.Location l ON l.LocId = s.LocId
JOIN wms.Item i     ON i.Mtrl  = s.Mtrl
GROUP BY s.LocId, l.Code, l.ZoneCode, s.Mtrl, i.Code
HAVING SUM(s.Q) <> 0;
GO
CREATE VIEW wms.vStockItem AS              -- σύνολο ανά είδος (για τον νυχτερινό έλεγχο με το SoftOne)
SELECT v.Mtrl, v.ItemCode,
       SUM(v.Qty) AS QtyAll,
       SUM(CASE WHEN z.CountsInS1 = 1 THEN v.Qty ELSE 0 END) AS QtyS1,
       SUM(CASE WHEN z.Sellable   = 1 THEN v.Qty ELSE 0 END) AS QtySellable
FROM wms.vStock v JOIN wms.Zone z ON z.ZoneCode = v.ZoneCode
GROUP BY v.Mtrl, v.ItemCode;
GO

-- ============================================================ 11. Αρχικά δεδομένα
INSERT wms.Zone (ZoneCode, Name, CountsInS1, Sellable) VALUES
 ('MAIN',    N'Κύρια (ράφια)',                1, 1),
 ('RCV',     N'Παραλαβή / προς τοποθέτηση',   1, 0),
 ('FAULTY',  N'Faulty',                       1, 0),
 ('SERVICE', N'Service / έλεγχος',            1, 0),
 ('RET',     N'Επιστροφές πελατών',           1, 0),
 ('RTS',     N'Προς επιστροφή σε προμηθευτή', 1, 0);
INSERT wms.Floor (Code, Name, Lvl, Speed) VALUES
 ('IS', N'Ισόγειο',    0, 'FAST'),
 ('YP', N'Υπόγειο',   -1, 'SLOW'),
 ('O1', N'1ος όροφος', 1, 'STATIC');
INSERT wms.Setting (SKey, SValue, Note) VALUES
 ('replen.time',  N'07:00', N'Ώρα που βγαίνει η λίστα αναπλήρωσης'),
 ('pick.minDays', N'2',     N'Ελάχιστο θέσης picking = μέρες πωλήσεων'),
 ('pick.maxDays', N'7',     N'Μέγιστο θέσης picking = μέρες πωλήσεων'),
 ('slow.days',    N'60',    N'Είδος στο IS χωρίς κίνηση τόσες μέρες → πρόταση να κατέβει');
GO

-- ============================================================ 12. Χρήστης SQL της εφαρμογής: βλέπει ΜΟΝΟ αυτή τη βάση, δεν σβήνει τίποτα
USE master;
GO
IF SUSER_ID(N'wms_app') IS NULL
  CREATE LOGIN wms_app WITH PASSWORD = N'<<ΚΩΔΙΚΟΣ_WMS>>', DEFAULT_DATABASE = GeekOnWMS, CHECK_POLICY = ON, CHECK_EXPIRATION = OFF;
GO
USE GeekOnWMS;
GO
IF USER_ID(N'wms_app') IS NULL CREATE USER wms_app FOR LOGIN wms_app;
ALTER ROLE db_datareader ADD MEMBER wms_app;
ALTER ROLE db_datawriter ADD MEMBER wms_app;
GRANT EXECUTE ON SCHEMA::wms TO wms_app;
DENY  DELETE  ON SCHEMA::wms TO wms_app;             -- δεύτερη ασφάλεια πάνω από τα triggers
DENY  UPDATE  ON wms.Movement TO wms_app;
DENY  UPDATE  ON wms.LoginLog TO wms_app;
GO

-- ============================================================ 13. Έλεγχος: πρέπει να βγάλει 6 ζώνες, 3 ορόφους, 4 ρυθμίσεις
SELECT (SELECT COUNT(*) FROM wms.Zone) AS Zones, (SELECT COUNT(*) FROM wms.Floor) AS Floors, (SELECT COUNT(*) FROM wms.Setting) AS Settings;
GO
SET NOEXEC OFF;
