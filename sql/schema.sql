-- VisionScore: Supabase schema for analysis_reports
-- Apply via Supabase SQL Editor or `supabase db push`

create extension if not exists "uuid-ossp";

create table analysis_reports (
    id uuid primary key default uuid_generate_v4(),
    created_at timestamptz default now(),

    -- Image metadata
    image_path text not null,
    image_url text,
    image_width int,
    image_height int,
    image_format text,

    -- Individual scores (JSONB for queryability)
    technical jsonb,
    aesthetic jsonb,
    composition jsonb,
    ai_feedback jsonb,

    -- Aggregated results
    overall_score float not null,
    grade text not null,
    analysis_time_seconds float,

    -- Full serialized AnalysisReport for exact reconstruction
    full_report jsonb not null,

    -- Batch support
    report_type text not null default 'single',
    batch_id uuid
);

-- Indexes
create index idx_reports_created_at on analysis_reports(created_at desc);
create index idx_reports_grade on analysis_reports(grade);
create index idx_reports_batch_id on analysis_reports(batch_id);
create index idx_reports_report_type on analysis_reports(report_type);

-- Storage bucket (run in Supabase dashboard or via API):
-- insert into storage.buckets (id, name, public) values ('images', 'images', true);

-- Row Level Security (uncomment when auth is enabled):
-- alter table analysis_reports enable row level security;
-- alter table analysis_reports add column user_id uuid references auth.users(id);
-- create policy "Users read own reports" on analysis_reports for select using (auth.uid() = user_id);
-- create policy "Users insert own reports" on analysis_reports for insert with check (auth.uid() = user_id);
-- create policy "Users delete own reports" on analysis_reports for delete using (auth.uid() = user_id);
