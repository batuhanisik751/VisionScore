# Supabase Schema Setup

## Prerequisites
- A Supabase project at [supabase.com](https://supabase.com)
- Project URL and anon/service-role keys from Settings > API

## Setup Steps

1. **Create the database table**: Open the SQL Editor in your Supabase dashboard and run the contents of `schema.sql`.

2. **Create the storage bucket**: Go to Storage in the dashboard and create a bucket named `images` with public access enabled.

3. **Configure environment variables**: Add your Supabase credentials to `.env`:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-key
   ```

4. **Optional - Enable RLS**: Uncomment the RLS policies in `schema.sql` and add a `user_id` column when you want per-user access control.
