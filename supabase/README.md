# Supabase setup

1. Create a new Supabase project in the dashboard.
2. Open SQL Editor and run the contents of `schema.sql`.
3. Replace the placeholder values below with your project URL and anon key before deploying.
4. Keep the same values across the public storefront and admin pages.

Example config object:

```js
window.__KINGDOM_SUPABASE_CONFIG__ = {
  url: 'https://your-project-ref.supabase.co',
  anonKey: 'your-anon-key'
};
```

The app will use localStorage as a fallback when Supabase is not configured yet.
