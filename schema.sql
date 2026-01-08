-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tenants Table
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    config JSONB DEFAULT '{}', -- Store tenant-specific configs here
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Price Lists Table
CREATE TABLE price_lists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    item_code VARCHAR(50), -- Optional code from Excel
    category VARCHAR(100),
    description TEXT NOT NULL,
    unit VARCHAR(50),
    unit_price NUMERIC(10, 2) NOT NULL,
    effective_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_item_tenant UNIQUE (tenant_id, description) -- Description implies uniqueness per tenant for matching
);

-- Product Aliases Table (Learning Loop)
CREATE TABLE product_aliases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    alias_text TEXT NOT NULL,
    price_list_id UUID REFERENCES price_lists(id) ON DELETE CASCADE,
    confidence_score FLOAT DEFAULT 1.0, -- 1.0 for human verified
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_alias_tenant UNIQUE (tenant_id, alias_text)
);

-- Quotations Table (Header)
CREATE TABLE quotations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    session_id VARCHAR(255), -- For linking to the chat/voice session
    client_name VARCHAR(255),
    total_amount NUMERIC(12, 2),
    status VARCHAR(50) DEFAULT 'draft', -- draft, finalized
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Quotation Items Table (Line Items)
CREATE TABLE quotation_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quotation_id UUID REFERENCES quotations(id) ON DELETE CASCADE,
    price_list_id UUID REFERENCES price_lists(id) ON DELETE SET NULL, -- Nullable if custom item
    description TEXT NOT NULL, -- Copied from price list or custom
    quantity NUMERIC(10, 2) NOT NULL DEFAULT 1, -- Can be area, count etc.
    unit_price NUMERIC(10, 2) NOT NULL,
    subtotal NUMERIC(12, 2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    confidence_score FLOAT, -- Match confidence
    is_suspense BOOLEAN DEFAULT FALSE, -- If true, needs review
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_price_lists_tenant ON price_lists(tenant_id);
CREATE INDEX idx_product_aliases_text ON product_aliases(alias_text);
CREATE INDEX idx_product_aliases_tenant ON product_aliases(tenant_id);
