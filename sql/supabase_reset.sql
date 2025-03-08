-- Reset script for ISONER Chatbot
-- This script drops all objects created in supabase_setup.sql

-- First drop RLS policies (they depend on functions)
DROP POLICY IF EXISTS "Admins can manage intents" ON intents;
DROP POLICY IF EXISTS "All users can view intents" ON intents;
DROP POLICY IF EXISTS "Users can view entities from their messages" ON entities;
DROP POLICY IF EXISTS "System can manage entities" ON entities;
DROP POLICY IF EXISTS "Users can manage their own conversations" ON conversations;
DROP POLICY IF EXISTS "Users can view their own messages" ON messages;
DROP POLICY IF EXISTS "Users can view their own profile" ON users;
DROP POLICY IF EXISTS "Admins can view all users" ON users;
DROP POLICY IF EXISTS "Admins can manage roles" ON roles;
DROP POLICY IF EXISTS "Admins can manage permissions" ON permissions;
DROP POLICY IF EXISTS "Admins can manage role permissions" ON role_permissions;
DROP POLICY IF EXISTS "Admins can manage user roles" ON user_roles;
DROP POLICY IF EXISTS "Users can view their own roles" ON user_roles;

-- Disable RLS on tables
ALTER TABLE IF EXISTS users DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS conversations DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS messages DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS intents DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS entities DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS roles DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS permissions DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS role_permissions DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS user_roles DISABLE ROW LEVEL SECURITY;

-- Drop functions with CASCADE to handle any remaining dependencies
DROP FUNCTION IF EXISTS get_role_permissions(UUID) CASCADE;
DROP FUNCTION IF EXISTS get_user_roles(UUID) CASCADE;
DROP FUNCTION IF EXISTS has_permission(UUID, TEXT) CASCADE;
DROP FUNCTION IF EXISTS get_conversation_messages(UUID) CASCADE;
DROP FUNCTION IF EXISTS get_user_conversations(UUID) CASCADE;
DROP FUNCTION IF EXISTS insert_bot_message(UUID, TEXT, TEXT) CASCADE;

-- Drop tables (in reverse order of dependencies)
DROP TABLE IF EXISTS user_roles CASCADE;
DROP TABLE IF EXISTS role_permissions CASCADE;
DROP TABLE IF EXISTS permissions CASCADE;
DROP TABLE IF EXISTS roles CASCADE;
DROP TABLE IF EXISTS entities CASCADE;
DROP TABLE IF EXISTS intents CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Notify completion
DO $$
BEGIN
  RAISE NOTICE 'Database reset complete. You can now run supabase_setup.sql';
END $$; 