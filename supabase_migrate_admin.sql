-- =============================================
-- MIGRATION: allow 'admin' at signup + bootstrap the first administrator
-- Run this ENTIRE script in Supabase SQL Editor.
--
-- NON-DESTRUCTIVE: this script does NOT drop any table and does not touch a
-- single row of student/session data. (Do NOT re-run supabase_schema.sql for
-- this — that file is a full reset and begins by DROPping every table.)
--
-- Why you need it: the previous version of protect_profile_role() silently
-- downgraded a self-asserted 'admin' to 'teacher' on INSERT. The result is a
-- project where NO profile has role='admin', so is_admin() is false for
-- everyone, RLS returns only each user's own rows, and the Admin Console renders
-- empty. Since only an admin can promote anyone, that state can't be escaped
-- from inside the app — it has to be broken here, once.
-- =============================================

-- ── STEP 0. Who should be the administrator? ────────────────────────────────
-- EDIT the email on the next line if this isn't the right account.
-- It must already exist in profiles (i.e. that person has signed up).
DO $$
DECLARE
  v_admin_email TEXT := 'utkarsh.ironman50@gmail.com';   -- <<< EDIT ME
  v_id UUID;
  v_old TEXT;
BEGIN
  SELECT id, role INTO v_id, v_old
  FROM profiles
  WHERE lower(email) = lower(v_admin_email)
  ORDER BY created_at NULLS LAST
  LIMIT 1;

  IF v_id IS NULL THEN
    RAISE EXCEPTION
      'No profile with email %. Sign in with that account once (so its profile row is created), then re-run this script. Existing emails: %',
      v_admin_email,
      (SELECT coalesce(string_agg(email, ', '), '(none)') FROM profiles);
  END IF;

  -- The role trigger below refuses role changes made by a non-admin, and the SQL
  -- editor has no auth.uid(), so is_admin() is false here. Disable the trigger
  -- for this one statement, then put it straight back.
  -- (If your role lacks permission for DISABLE TRIGGER, delete these two ALTER
  -- lines and instead run STEP 1 first, then this block — the trigger is dropped
  -- and recreated there, so a plain UPDATE in between would go through.)
  ALTER TABLE profiles DISABLE TRIGGER protect_profile_role_trigger;
  UPDATE profiles SET role = 'admin', updated_at = NOW() WHERE id = v_id;
  ALTER TABLE profiles ENABLE TRIGGER protect_profile_role_trigger;

  RAISE NOTICE 'Promoted % (%): % -> admin', v_admin_email, v_id, v_old;
END $$;

-- ── STEP 1. Replace the role guard (function body only — no drops) ──────────
--  INSERT: any role from the signup form is accepted, INCLUDING 'admin' — the
--          signup screen deliberately offers Teacher / Parent / Admin. Unknown
--          roles are clamped to 'teacher'.
--  UPDATE: only an admin may change a role at all; unknown roles are rejected.
--          This still prevents an EXISTING account from being escalated after
--          the fact (e.g. a teacher PATCHing their own role to admin).
CREATE OR REPLACE FUNCTION protect_profile_role()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    IF NEW.role NOT IN ('admin', 'teacher', 'parent', 'sponsor') THEN
      NEW.role := 'teacher';
    END IF;
  ELSIF TG_OP = 'UPDATE' THEN
    IF NEW.role IS DISTINCT FROM OLD.role AND NOT is_admin() THEN
      NEW.role := OLD.role;
    END IF;
    IF NEW.role NOT IN ('admin', 'teacher', 'parent', 'sponsor') THEN
      NEW.role := OLD.role;
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Make sure the trigger exists and is enabled (harmless if it already is).
DROP TRIGGER IF EXISTS protect_profile_role_trigger ON profiles;
CREATE TRIGGER protect_profile_role_trigger
  BEFORE INSERT OR UPDATE ON profiles
  FOR EACH ROW EXECUTE FUNCTION protect_profile_role();

-- ── STEP 2. Confirm the result ──────────────────────────────────────────────
SELECT role, count(*) AS accounts FROM profiles GROUP BY role ORDER BY role;
SELECT id, email, username, full_name, role FROM profiles ORDER BY role, email;
