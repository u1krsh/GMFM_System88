-- =============================================
-- GMFM System88 / MotorMeasure — Supabase Schema
-- Run this ENTIRE script in Supabase SQL Editor
-- Dashboard -> SQL Editor -> New Query -> Paste -> Run
-- =============================================

-- 0. Clean slate — drop everything
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
DROP FUNCTION IF EXISTS handle_new_user() CASCADE;
DROP FUNCTION IF EXISTS is_admin() CASCADE;
DROP FUNCTION IF EXISTS user_has_student_access(BIGINT) CASCADE;
DROP FUNCTION IF EXISTS user_owns_student(BIGINT) CASCADE;

-- Drop policies first (they reference tables)
DO $$ BEGIN
  -- profiles
  EXECUTE 'DROP POLICY IF EXISTS profiles_select ON profiles';
  EXECUTE 'DROP POLICY IF EXISTS profiles_insert ON profiles';
  EXECUTE 'DROP POLICY IF EXISTS profiles_update ON profiles';
  -- students
  EXECUTE 'DROP POLICY IF EXISTS students_select ON students';
  EXECUTE 'DROP POLICY IF EXISTS students_insert ON students';
  EXECUTE 'DROP POLICY IF EXISTS students_update ON students';
  EXECUTE 'DROP POLICY IF EXISTS students_delete ON students';
  -- sessions
  EXECUTE 'DROP POLICY IF EXISTS sessions_select ON sessions';
  EXECUTE 'DROP POLICY IF EXISTS sessions_insert ON sessions';
  EXECUTE 'DROP POLICY IF EXISTS sessions_update ON sessions';
  EXECUTE 'DROP POLICY IF EXISTS sessions_delete ON sessions';
  -- student_access
  EXECUTE 'DROP POLICY IF EXISTS student_access_select ON student_access';
  EXECUTE 'DROP POLICY IF EXISTS student_access_insert ON student_access';
  EXECUTE 'DROP POLICY IF EXISTS student_access_delete ON student_access';
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DROP TABLE IF EXISTS student_access CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;
DROP TABLE IF EXISTS students CASCADE;
DROP TABLE IF EXISTS sync_metadata CASCADE;
DROP TABLE IF EXISTS profiles CASCADE;

-- =============================================
-- 1. PROFILES
-- =============================================
CREATE TABLE profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name TEXT NOT NULL DEFAULT '',
  role TEXT NOT NULL DEFAULT 'teacher',
  email TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- 2. STUDENTS
-- =============================================
CREATE TABLE students (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  created_by UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  local_id INTEGER NOT NULL,
  given_name TEXT DEFAULT '',
  family_name TEXT DEFAULT '',
  dob TEXT,
  identifier TEXT,
  deleted BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(created_by, local_id)
);

-- =============================================
-- 3. SESSIONS
-- =============================================
CREATE TABLE sessions (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  created_by UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  local_id INTEGER NOT NULL,
  student_local_id INTEGER NOT NULL DEFAULT 0,
  scale TEXT DEFAULT '88',
  raw_scores TEXT DEFAULT '{}',
  total_score REAL DEFAULT 0,
  notes TEXT,
  deleted BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(created_by, local_id)
);

-- =============================================
-- 4. STUDENT_ACCESS (parent/sponsor linking)
-- =============================================
CREATE TABLE student_access (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  student_id BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  access_level TEXT NOT NULL DEFAULT 'view',
  granted_by UUID REFERENCES profiles(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(student_id, user_id)
);

-- =============================================
-- 5. HELPER FUNCTIONS (SECURITY DEFINER to avoid recursion)
-- =============================================

-- Check if current user is admin
CREATE OR REPLACE FUNCTION is_admin()
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'
  );
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- Check if current user has access to a specific student (via student_access)
-- SECURITY DEFINER bypasses RLS on student_access, breaking the recursion
CREATE OR REPLACE FUNCTION user_has_student_access(p_student_id BIGINT)
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM student_access WHERE student_id = p_student_id AND user_id = auth.uid()
  );
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- Check if current user owns a student (via students.created_by)
-- SECURITY DEFINER bypasses RLS on students, breaking the recursion
CREATE OR REPLACE FUNCTION user_owns_student(p_student_id BIGINT)
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM students WHERE id = p_student_id AND created_by = auth.uid()
  );
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- =============================================
-- 6. ROW LEVEL SECURITY
-- =============================================

-- PROFILES (simple — no cross-table refs)
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "profiles_select" ON profiles
  FOR SELECT USING (true);

CREATE POLICY "profiles_insert" ON profiles
  FOR INSERT WITH CHECK (auth.uid() = id);

CREATE POLICY "profiles_update" ON profiles
  FOR UPDATE USING (auth.uid() = id OR is_admin());

-- STUDENTS (uses function call to check student_access — no recursion)
ALTER TABLE students ENABLE ROW LEVEL SECURITY;

CREATE POLICY "students_select" ON students
  FOR SELECT USING (
    created_by = auth.uid()
    OR is_admin()
    OR user_has_student_access(id)
  );

CREATE POLICY "students_insert" ON students
  FOR INSERT WITH CHECK (created_by = auth.uid());

CREATE POLICY "students_update" ON students
  FOR UPDATE USING (created_by = auth.uid() OR is_admin());

CREATE POLICY "students_delete" ON students
  FOR DELETE USING (created_by = auth.uid() OR is_admin());

-- SESSIONS (uses function call — no recursion)
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "sessions_select" ON sessions
  FOR SELECT USING (
    created_by = auth.uid()
    OR is_admin()
  );

CREATE POLICY "sessions_insert" ON sessions
  FOR INSERT WITH CHECK (created_by = auth.uid());

CREATE POLICY "sessions_update" ON sessions
  FOR UPDATE USING (created_by = auth.uid() OR is_admin());

CREATE POLICY "sessions_delete" ON sessions
  FOR DELETE USING (created_by = auth.uid() OR is_admin());

-- STUDENT_ACCESS (uses function call — no recursion)
ALTER TABLE student_access ENABLE ROW LEVEL SECURITY;

CREATE POLICY "student_access_select" ON student_access
  FOR SELECT USING (
    user_id = auth.uid()
    OR is_admin()
    OR user_owns_student(student_id)
  );

CREATE POLICY "student_access_insert" ON student_access
  FOR INSERT WITH CHECK (
    is_admin()
    OR user_owns_student(student_id)
  );

CREATE POLICY "student_access_delete" ON student_access
  FOR DELETE USING (
    is_admin()
    OR user_owns_student(student_id)
  );

-- =============================================
-- 7. INDEXES
-- =============================================
CREATE INDEX idx_students_created_by ON students(created_by);
CREATE INDEX idx_sessions_created_by ON sessions(created_by);
CREATE INDEX idx_sessions_student ON sessions(created_by, student_local_id);
CREATE INDEX idx_student_access_user ON student_access(user_id);
CREATE INDEX idx_student_access_student ON student_access(student_id);
CREATE INDEX idx_profiles_role ON profiles(role);

-- =============================================
-- 8. TABLE GRANTS (required for RLS to work)
-- =============================================
GRANT SELECT, INSERT, UPDATE ON profiles TO authenticated;
GRANT SELECT ON profiles TO anon;

GRANT SELECT, INSERT, UPDATE, DELETE ON students TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON sessions TO authenticated;
GRANT SELECT, INSERT, DELETE ON student_access TO authenticated;

GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- =============================================
-- DONE
-- =============================================
SELECT 'Schema created successfully!' as result;
