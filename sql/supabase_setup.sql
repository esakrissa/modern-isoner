-- Combined Setup for ISONER Chatbot

-- Users table
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_login TIMESTAMP WITH TIME ZONE
);

-- Conversations table
CREATE TABLE conversations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id),
  started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_message_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  status TEXT DEFAULT 'active'
);

-- Messages table
CREATE TABLE messages (
  id UUID PRIMARY KEY,
  conversation_id UUID REFERENCES conversations(id),
  sender_type TEXT NOT NULL, -- 'user' or 'bot'
  content TEXT NOT NULL,
  content_type TEXT DEFAULT 'text', -- 'text', 'image', 'location', etc.
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  processed BOOLEAN DEFAULT FALSE
);

-- Intents table
CREATE TABLE intents (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT UNIQUE NOT NULL,
  description TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Entities table
CREATE TABLE entities (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  message_id UUID REFERENCES messages(id),
  name TEXT NOT NULL,
  value TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RBAC Tables

-- Roles table
CREATE TABLE roles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT UNIQUE NOT NULL,
  description TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Permissions table
CREATE TABLE permissions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT UNIQUE NOT NULL,
  description TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Role-Permission mapping
CREATE TABLE role_permissions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
  permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(role_id, permission_id)
);

-- User-Role mapping
CREATE TABLE user_roles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id, role_id)
);

-- Insert default intents
INSERT INTO intents (name, description) VALUES
  ('general_query', 'General questions or chitchat'),
  ('hotel_search', 'Search for hotels'),
  ('hotel_booking', 'Book a hotel'),
  ('cancel_booking', 'Cancel a hotel booking');

-- Service role function to allow backend services to insert bot messages
CREATE FUNCTION insert_bot_message(
  p_conversation_id UUID,
  p_content TEXT,
  p_content_type TEXT DEFAULT 'text'
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_message_id UUID;
BEGIN
  v_message_id := uuid_generate_v4();
  
  INSERT INTO messages (
    id,
    conversation_id,
    sender_type,
    content,
    content_type,
    created_at,
    processed
  ) VALUES (
    v_message_id,
    p_conversation_id,
    'bot',
    p_content,
    p_content_type,
    NOW(),
    TRUE
  );
  
  RETURN v_message_id;
END;
$$;

-- Create function to get user's conversations
CREATE FUNCTION get_user_conversations(p_user_id UUID)
RETURNS TABLE (
  id UUID,
  started_at TIMESTAMP WITH TIME ZONE,
  last_message_at TIMESTAMP WITH TIME ZONE,
  status TEXT,
  last_message TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    c.id,
    c.started_at,
    c.last_message_at,
    c.status,
    (
      SELECT m.content
      FROM messages m
      WHERE m.conversation_id = c.id
      ORDER BY m.created_at DESC
      LIMIT 1
    ) as last_message
  FROM conversations c
  WHERE c.user_id = p_user_id
  ORDER BY c.last_message_at DESC;
END;
$$;

-- Create function to get conversation messages
CREATE FUNCTION get_conversation_messages(p_conversation_id UUID)
RETURNS TABLE (
  id UUID,
  sender_type TEXT,
  content TEXT,
  content_type TEXT,
  created_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    m.id,
    m.sender_type,
    m.content,
    m.content_type,
    m.created_at
  FROM messages m
  WHERE m.conversation_id = p_conversation_id
  ORDER BY m.created_at ASC;
END;
$$;

-- RBAC Functions

-- Function to check if user has a specific permission
CREATE OR REPLACE FUNCTION has_permission(p_user_id UUID, p_permission_name TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_has_permission BOOLEAN;
BEGIN
  SELECT EXISTS (
    SELECT 1
    FROM user_roles ur
    JOIN role_permissions rp ON ur.role_id = rp.role_id
    JOIN permissions p ON rp.permission_id = p.id
    WHERE ur.user_id = p_user_id AND p.name = p_permission_name
  ) INTO v_has_permission;
  
  RETURN v_has_permission;
END;
$$;

-- Function to get user's roles
CREATE OR REPLACE FUNCTION get_user_roles(p_user_id UUID)
RETURNS TABLE (
  id UUID,
  name TEXT,
  description TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  SELECT r.id, r.name, r.description
  FROM roles r
  JOIN user_roles ur ON r.id = ur.role_id
  WHERE ur.user_id = p_user_id;
END;
$$;

-- Function to get role's permissions
CREATE OR REPLACE FUNCTION get_role_permissions(p_role_id UUID)
RETURNS TABLE (
  id UUID,
  name TEXT,
  description TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  SELECT p.id, p.name, p.description
  FROM permissions p
  JOIN role_permissions rp ON p.id = rp.permission_id
  WHERE rp.role_id = p_role_id;
END;
$$;

-- Insert default roles
INSERT INTO roles (name, description) VALUES
  ('admin', 'Administrator with full access'),
  ('manager', 'Manager with limited administrative access'),
  ('user', 'Regular user with basic access');

-- Insert default permissions
INSERT INTO permissions (name, description) VALUES
  ('view_users', 'Can view user list'),
  ('manage_users', 'Can create, update, and delete users'),
  ('view_conversations', 'Can view conversation history'),
  ('manage_conversations', 'Can manage conversations'),
  ('assign_roles', 'Can assign roles to users'),
  ('manage_permissions', 'Can manage role permissions'),
  ('view_analytics', 'Can view analytics data'),
  ('export_data', 'Can export data');

-- Assign permissions to roles
-- Admin role (all permissions)
INSERT INTO role_permissions (role_id, permission_id)
SELECT 
  (SELECT id FROM roles WHERE name = 'admin'),
  id
FROM permissions;

-- Manager role
INSERT INTO role_permissions (role_id, permission_id)
SELECT 
  (SELECT id FROM roles WHERE name = 'manager'),
  id
FROM permissions
WHERE name IN ('view_users', 'view_conversations', 'view_analytics', 'export_data');

-- User role
INSERT INTO role_permissions (role_id, permission_id)
SELECT 
  (SELECT id FROM roles WHERE name = 'user'),
  id
FROM permissions
WHERE name IN ('view_conversations');

-- Enable Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE role_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE intents ENABLE ROW LEVEL SECURITY;
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;

-- RLS Policies

-- Users policy
CREATE POLICY "Users can view their own data" ON users
  FOR SELECT USING (auth.uid() = id);

-- Conversations policy
CREATE POLICY "Users can view their own conversations" ON conversations
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own conversations" ON conversations
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Messages policy
CREATE POLICY "Users can view messages in their conversations" ON messages
  FOR SELECT USING (
    conversation_id IN (
      SELECT id FROM conversations WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "Users can insert messages in their conversations" ON messages
  FOR INSERT WITH CHECK (
    conversation_id IN (
      SELECT id FROM conversations WHERE user_id = auth.uid()
    )
  );

-- Roles policies
CREATE POLICY "Admins can manage roles" ON roles
  FOR ALL USING (
    has_permission(auth.uid(), 'manage_permissions')
  );
  
CREATE POLICY "All users can view roles" ON roles
  FOR SELECT USING (true);

-- Permissions policies
CREATE POLICY "Admins can manage permissions" ON permissions
  FOR ALL USING (
    has_permission(auth.uid(), 'manage_permissions')
  );
  
CREATE POLICY "All users can view permissions" ON permissions
  FOR SELECT USING (true);

-- Role-Permission policies
CREATE POLICY "Admins can manage role permissions" ON role_permissions
  FOR ALL USING (
    has_permission(auth.uid(), 'manage_permissions')
  );
  
CREATE POLICY "All users can view role permissions" ON role_permissions
  FOR SELECT USING (true);

-- User-Role policies
CREATE POLICY "Admins can manage user roles" ON user_roles
  FOR ALL USING (
    has_permission(auth.uid(), 'assign_roles')
  );
  
CREATE POLICY "Users can view their own roles" ON user_roles
  FOR SELECT USING (
    auth.uid() = user_id OR has_permission(auth.uid(), 'view_users')
  );

-- Intents policies
CREATE POLICY "Admins can manage intents" ON intents
  FOR ALL USING (
    has_permission(auth.uid(), 'manage_permissions')
  );
  
CREATE POLICY "All users can view intents" ON intents
  FOR SELECT USING (true);

-- Entities policies
CREATE POLICY "Users can view entities from their messages" ON entities
  FOR SELECT USING (
    message_id IN (
      SELECT m.id FROM messages m
      JOIN conversations c ON m.conversation_id = c.id
      WHERE c.user_id = auth.uid()
    )
  );

CREATE POLICY "System can manage entities" ON entities
  FOR ALL USING (
    has_permission(auth.uid(), 'manage_permissions')
  ); 