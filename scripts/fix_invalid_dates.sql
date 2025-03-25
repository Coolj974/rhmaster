-- Désactiver les contraintes de clés étrangères
PRAGMA foreign_keys=off;

-- Démarrer une transaction
BEGIN TRANSACTION;

-- Mettre à jour les dates invalides dans ExpenseReport
UPDATE rh_management_expensereport 
SET created_at = CURRENT_TIMESTAMP 
WHERE created_at LIKE '%' || char(160) || '%' OR created_at IS NULL;

UPDATE rh_management_expensereport 
SET updated_at = CURRENT_TIMESTAMP 
WHERE updated_at LIKE '%' || char(160) || '%' OR updated_at IS NULL;

-- Mettre à jour les dates invalides dans LeaveRequest
UPDATE rh_management_leaverequest 
SET created_at = CURRENT_TIMESTAMP 
WHERE created_at LIKE '%' || char(160) || '%' OR created_at IS NULL;

UPDATE rh_management_leaverequest 
SET updated_at = CURRENT_TIMESTAMP 
WHERE updated_at LIKE '%' || char(160) || '%' OR updated_at IS NULL;

-- Mettre à jour les dates invalides dans KilometricExpense
UPDATE rh_management_kilometricexpense 
SET created_at = CURRENT_TIMESTAMP 
WHERE created_at LIKE '%' || char(160) || '%' OR created_at IS NULL;

UPDATE rh_management_kilometricexpense 
SET updated_at = CURRENT_TIMESTAMP 
WHERE updated_at LIKE '%' || char(160) || '%' OR updated_at IS NULL;

-- Nettoyage des migrations problématiques
DELETE FROM django_migrations WHERE app='rh_management' AND name LIKE '0026_%';
DELETE FROM django_migrations WHERE app='rh_management' AND name LIKE '0027_%';

-- Valider les modifications
COMMIT;

-- Réactiver les contraintes de clés étrangères
PRAGMA foreign_keys=on;
