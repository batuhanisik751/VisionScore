-- Phase 9.8: Mobile-Friendly API tables
-- Run this migration against your Supabase project.

-- API Keys for authentication
create table if not exists api_keys (
    id uuid primary key default uuid_generate_v4(),
    created_at timestamptz not null default now(),
    name text not null,
    key_hash text not null unique,
    key_prefix text not null,
    is_active boolean not null default true,
    rate_limit_per_minute int not null default 60,
    last_used_at timestamptz
);
create index if not exists idx_api_keys_key_hash on api_keys(key_hash);

-- Webhook registrations
create table if not exists webhooks (
    id uuid primary key default uuid_generate_v4(),
    created_at timestamptz not null default now(),
    url text not null,
    events text[] not null default '{analysis.completed,batch.completed}',
    secret text,
    is_active boolean not null default true,
    last_triggered_at timestamptz,
    failure_count int not null default 0,
    api_key_id uuid references api_keys(id) on delete set null
);
create index if not exists idx_webhooks_active on webhooks(is_active) where is_active = true;

-- Webhook delivery log
create table if not exists webhook_deliveries (
    id uuid primary key default uuid_generate_v4(),
    created_at timestamptz not null default now(),
    webhook_id uuid not null references webhooks(id) on delete cascade,
    event text not null,
    payload jsonb not null,
    status_code int,
    response_body text,
    success boolean not null default false,
    attempt int not null default 1,
    next_retry_at timestamptz
);
create index if not exists idx_deliveries_webhook on webhook_deliveries(webhook_id);
create index if not exists idx_deliveries_retry on webhook_deliveries(next_retry_at)
    where success = false;
