import psycopg2
import urllib.request

conn_str = 'postgresql://postgres:8S1MlkL4agLwj@db.spckgpxzcxvogjamfsqr.supabase.co:5432/postgres?sslmode=require'
conn = psycopg2.connect(conn_str)
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS vehicles_images_backup AS SELECT id, images, now() AS backed_at FROM vehicles WHERE images::text LIKE '%/storage/v1/object/public/images/%';")
cur.execute("""
CREATE OR REPLACE FUNCTION replace_images_bucket(old_bucket text, new_bucket text)
RETURNS integer AS $$
DECLARE
  v_count integer := 0;
BEGIN
  UPDATE vehicles
  SET images = (
    SELECT jsonb_agg(
      CASE
        WHEN elem LIKE ('%' || '/storage/v1/object/public/' || old_bucket || '/%')
          THEN replace(elem, '/storage/v1/object/public/' || old_bucket || '/', '/storage/v1/object/public/' || new_bucket || '/')
        ELSE elem::text
      END
    )::jsonb
    FROM jsonb_array_elements_text(images) AS t(elem)
  )
  WHERE images::text LIKE ('%' || '/storage/v1/object/public/' || old_bucket || '/%');

  GET DIAGNOSTICS v_count = ROW_COUNT;
  RETURN v_count;
END;
$$ LANGUAGE plpgsql;
""")
conn.commit()

cur.execute("SELECT replace_images_bucket(%s, %s);", ('images', 'public'))
rows_affected = cur.fetchone()[0]
print(f'ROWS_UPDATED={rows_affected}')

cur.execute("SELECT id, images FROM vehicles WHERE images::text LIKE '%/storage/v1/object/public/public/%' LIMIT 3;")
rows = cur.fetchall()
print('SAMPLE_ROWS=' + str(rows[:3]))

url = 'https://spckgpxzcxvogjamfsqr.supabase.co/storage/v1/object/public/public/Kingdom_AutoMobile/43c4f623335449c4a301c41224f4ac46-.webp'
try:
    req = urllib.request.Request(url, method='HEAD')
    with urllib.request.urlopen(req, timeout=30) as resp:
        print('URL_STATUS=' + str(resp.status))
        print('URL_CONTENT_TYPE=' + str(resp.headers.get('Content-Type')))
except Exception as e:
    print('URL_ERROR=' + str(type(e).__name__) + ': ' + str(e))

conn.close()
