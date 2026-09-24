#!/usr/bin/env python3
"""
Generate a static vehicle HTML page from the template.

Usage:
  python tools/generate_vehicle.py --id land-cruiser --title "Toyota Land Cruiser" --price "GH₵48,500" \
    --year 2021 --transmission Automatic --fuel Petrol --mileage "45,000 km" \
    --vin JT123456789012345 --condition "Used - Excellent" --history "Imported from Japan..." \
    --images images/land-cruiser/1.jpg,images/land-cruiser/2.jpg

The script will create `vehicle-<id>.html` in the repo root.
"""
import argparse
import os
import os.path
try:
  from PIL import Image
  PIL_AVAILABLE = True
except Exception:
  PIL_AVAILABLE = False
from string import Template

TEMPLATE = Template('''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>$title — Kingdom AutoMobile</title>
  <link rel="stylesheet" href="styles.css" />
  <link rel="stylesheet" href="vehicle.css" />
</head>
<body>
<header class="topbar">
  <div class="container nav">
    <a class="brand" href="index.html"><span class="brand-mark">KA</span><span>Kingdom <b>AutoMobile</b><small>DEALERSHIP</small></span></a>
    <button class="menu-btn" aria-label="Open menu">☰</button>
    <nav>
      <a href="index.html">Home</a><a href="stock.html">Stock</a><a href="how.html">How to Buy</a>
      <a href="about.html">About Us</a><a href="contact.html">Contact</a>
      <a class="login" href="login.html">Login</a><a class="signup" href="signup.html">Sign Up</a>
    </nav>
  </div>
</header>

<main class="vehicle-hero container">
  <div class="vehicle-container">
    <div>
      <div class="gallery">
        <div id="mainImage" class="main-image">$main_image_html</div>
        <div id="thumbs" class="thumbs">$thumbs_html</div>
      </div>
      <div id="description" class="description">$description</div>
      <div class="vehicle-meta">
        <dl>
          <dt>Brand</dt><dd>$brand</dd>
          <dt>Year / Model</dt><dd>$year_model</dd>
          <dt>Engine</dt><dd>$engine_capacity</dd>
          <dt>VIN</dt><dd>$vin</dd>
          <dt>Condition</dt><dd>$condition</dd>
          <dt>Mileage</dt><dd>$mileage</dd>
          <dt>Location</dt><dd>$location</dd>
        </dl>
        <div class="vehicle-history"><strong>History:</strong><p>$history</p></div>
      </div>
    </div>

    <aside class="details-card">
      <h2>$title</h2>
      <div class="price">$price</div>
      <div class="specs">
        <div><b>$year</b><small>$transmission</small></div>
        <div><b>$fuel</b><small>$mileage</small></div>
      </div>
      <div id="extraDetails">
        <p><b>Brand:</b> $brand</p>
        <p><b>Model:</b> $year_model</p>
        <p><b>Engine Capacity:</b> $engine_capacity</p>
        <p><b>Mileage:</b> $mileage</p>
        <p><b>Transmission:</b> $transmission</p>
        <p><b>Fuel:</b> $fuel</p>
        <p><b>Price Range:</b> $price_range</p>
        <p><b>Shipping Cost:</b> $shipping_cost</p>
        <p><b>Service Fees:</b> $service_fees</p>
        <p><b>Duty:</b> $duty</p>
        <p><b>Port Charges:</b> $port_charges</p>
        <p><b>Total Landed Cost:</b> $total_landed_cost</p>
        <p><b>Current Location:</b> $current_location</p>
      </div>
      <div class="inquiry"><button id="inquireBtn">Send Inquiry</button></div>
    </aside>
  </div>
</main>

<footer><div class="container footer"><div class="brand"><span class="brand-mark">KA</span><span>Kingdom <b>AutoMobile</b><small>DEALERSHIP</small></span></div><p>© 2026 Kingdom AutoMobile Dealership. All rights reserved.</p></div></footer>

<script>
document.addEventListener('DOMContentLoaded', function(){
document.addEventListener('DOMContentLoaded', function(){
  document.querySelectorAll('.thumb').forEach(t=>t.addEventListener('click', ()=>{ document.querySelectorAll('.thumb').forEach(x=>x.classList.remove('active')); t.classList.add('active'); document.getElementById('mainImage').innerHTML = t.innerHTML;}));
  const menuBtn = document.querySelector('.menu-btn');
  const nav = document.querySelector('nav');
  if (menuBtn && nav){ menuBtn.addEventListener('click', ()=>nav.classList.toggle('show')); nav.querySelectorAll('a').forEach(link=>link.addEventListener('click', ()=>nav.classList.remove('show'))); }
  const inquire = document.getElementById('inquireBtn');
  if(inquire){
    inquire.addEventListener('click', function(){
      try{
        const name = prompt('Your name (optional)') || '';
        const contact = prompt('Your email or phone') || '';
        const message = prompt('Message') || '';
        const rec = { vehicle: '$title', id: '$id', name, contact, message, ts: Date.now() };
        const list = JSON.parse(localStorage.getItem('inquiries')||'[]');
        list.push(rec); localStorage.setItem('inquiries', JSON.stringify(list));
        alert('Your inquiry has been sent. Our team will contact you shortly.');
      }catch(e){ alert('Your inquiry has been sent. Our team will contact you shortly.') }
    });
  }
});
</script>
</body>
</html>
''')

def make_img_tag(src, alt='', cls='', style=''):
    return f'<img src="{src}" alt="{alt}" class="{cls}" style="{style}"/>'

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--id', required=True)
    p.add_argument('--title', required=True)
    p.add_argument('--price', required=True)
    p.add_argument('--year', required=True)
    p.add_argument('--transmission', default='')
    p.add_argument('--fuel', default='')
    p.add_argument('--mileage', default='')
    p.add_argument('--vin', default='')
    p.add_argument('--condition', default='')
    p.add_argument('--history', default='')
    p.add_argument('--location', default='Tamale')
    p.add_argument('--brand', default='')
    p.add_argument('--year-model', default='')
    p.add_argument('--engine-capacity', default='')
    p.add_argument('--price-range', default='')
    p.add_argument('--shipping-cost', default='')
    p.add_argument('--service-fees', default='')
    p.add_argument('--duty', default='')
    p.add_argument('--port-charges', default='')
    p.add_argument('--total-landed-cost', default='')
    p.add_argument('--current-location', default='')
    p.add_argument('--images', default='')
    args = p.parse_args()

    images = [s.strip() for s in args.images.split(',') if s.strip()]
    if images:
      main_image_html = make_img_tag(images[0], args.title+' main', '', 'max-width:100%;max-height:100%;object-fit:cover;border-radius:6px')
      thumbs = []
      for i, src in enumerate(images):
          cls = 'active' if i == 0 else ''
          thumb_img = make_img_tag(src, f'thumb {i+1}', '', 'width:100%;height:100%;object-fit:cover;border-radius:6px')
          thumbs.append(f'<div class="thumb {cls}">' + thumb_img + '</div>')
      thumbs_html = ''.join(thumbs)
    else:
        main_image_html = args.title
        thumbs_html = ''

    # Normalize price to use HTML entity for cedi to avoid encoding issues when writing files
    safe_price = args.price.replace('₵', '&#8355;') if args.price else args.price
    safe_price_range = args.price_range.replace('₵', '&#8355;') if args.price_range else args.price_range

    out = TEMPLATE.substitute(
      title=args.title,
      price=safe_price,
      year=args.year,
      transmission=args.transmission,
      fuel=args.fuel,
      mileage=args.mileage,
      vin=args.vin,
      condition=args.condition,
      history=args.history,
      id=args.id,
      location=args.location,
      brand=args.brand or 'N/A',
      year_model=args.year_model or args.year,
      engine_capacity=args.engine_capacity or 'N/A',
      price_range=safe_price_range or 'N/A',
      shipping_cost=args.shipping_cost or 'N/A',
      service_fees=args.service_fees or 'N/A',
      duty=args.duty or 'N/A',
      port_charges=args.port_charges or 'N/A',
      total_landed_cost=args.total_landed_cost or 'N/A',
      current_location=args.current_location or args.location,
      description=args.history or '',
      main_image_html=main_image_html,
      thumbs_html=thumbs_html
    )

    out_path = f'vehicle-{args.id}.html'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(out)
    print('Wrote', out_path)
    # Insert a vehicle card into stock.html and index.html (top of grid). Avoid duplicates.
    repo_root = os.path.dirname(os.path.dirname(__file__))
    stock_path = os.path.join(repo_root, 'stock.html')
    target_link = f'vehicle-{args.id}.html'

    # Build thumbnail if possible (save under images/<id>/thumb.jpg)
    thumb_rel = None
    if images:
      first_img = images[0]
      src_img = os.path.join(repo_root, first_img.replace('/', os.sep))
      thumb_dir = os.path.join(repo_root, 'images', args.id)
      os.makedirs(thumb_dir, exist_ok=True)
      thumb_path = os.path.join(thumb_dir, 'thumb.jpg')
      if PIL_AVAILABLE and os.path.exists(src_img):
        try:
          im = Image.open(src_img)
          im.thumbnail((400, 300))
          im.save(thumb_path, quality=85)
          thumb_rel = os.path.relpath(thumb_path, repo_root).replace('\\', '/')
        except Exception as e:
          print('Thumbnail generation failed:', e)
      # fallback to original image if thumbnail not created
      if not thumb_rel:
        thumb_rel = first_img

    # build vehicle card HTML (use thumb_rel if available)
    if thumb_rel:
      img_tag = make_img_tag(thumb_rel, args.title, '', 'width:100%;height:100%;object-fit:cover;border-radius:6px')
      vehicle_img_html = f'<div class="vehicle-img"><span class="tag">Available</span><div class="car-placeholder">{img_tag}</div></div>'
    else:
      parts = args.title.split()
      make_lbl = parts[0].upper() if parts else ''
      model_lbl = parts[1] if len(parts) > 1 else ''
      vehicle_img_html = f'<div class="vehicle-img"><span class="tag">Available</span><div class="car-placeholder">{make_lbl}<br><small>{model_lbl}</small></div></div>'

    brand_label = (args.brand or 'Vehicle').strip()
    year_model_label = (args.year_model or args.year).strip()
    location_label = (args.current_location or args.location or 'Location TBA').strip()
    price_range_label = (safe_price_range or safe_price or args.price).strip()
    extra_bits = []
    if brand_label and brand_label != 'Vehicle':
      extra_bits.append(f'Brand: {brand_label}')
    if year_model_label:
      extra_bits.append(f'Model: {year_model_label}')
    if price_range_label:
      extra_bits.append(f'Range: {price_range_label}')
    if location_label:
      extra_bits.append(f'Location: {location_label}')
    extra_html = '<div class="vehicle-meta-inline">' + ' • '.join(extra_bits) + '</div>' if extra_bits else ''

    card = f'''      <article class="vehicle-card">
      {vehicle_img_html}
      <div class="vehicle-info"><h3>{args.title}</h3><p>{args.year} • {args.transmission or 'Automatic'} • {args.fuel or 'Fuel'}</p><div class="price">{safe_price} <a class="view-details" href="{target_link}">View Details</a></div>{extra_html}</div>
      </article>
  '''

    # Update stock.html
    try:
      with open(stock_path, 'r', encoding='utf-8') as f:
        stock_html = f.read()
    except FileNotFoundError:
      print('stock.html not found; skipping stock update')
      stock_html = None

    if stock_html is not None:
      if target_link in stock_html:
        print('Stock already contains entry for', target_link)
      else:
        grid_start = stock_html.find('<div id="inventoryGrid"')
        if grid_start == -1:
          print('Could not find inventoryGrid in stock.html; skipping stock update')
        else:
          open_tag_end = stock_html.find('>', grid_start) + 1
          new_stock = stock_html[:open_tag_end] + '\n' + card + stock_html[open_tag_end:]
          with open(stock_path, 'w', encoding='utf-8') as f:
            f.write(new_stock)
          print('Inserted vehicle card at top of stock.html')

    # Update index.html preview if present
    index_path = os.path.join(repo_root, 'index.html')
    try:
      with open(index_path, 'r', encoding='utf-8') as f:
        index_html = f.read()
    except FileNotFoundError:
      index_html = None

    if index_html is not None:
      if target_link in index_html:
        print('Index already references', target_link)
      else:
        comment = '<!-- Stock moved to stock.html -->'
        if comment in index_html:
          # insert a small preview grid after the comment
          preview_section = f'''<!-- Stock preview (auto-inserted) -->\n<section class="section container">\n  <div class="vehicle-grid">\n{card}  </div>\n</section>\n'''
          index_html = index_html.replace(comment, comment + '\n' + preview_section)
          with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_html)
          print('Updated index.html with preview card')
        else:
          # fallback: try to find the featured inventory container and insert at top
          grid_start = index_html.find('<div id="featuredVehicles"')
          if grid_start != -1:
            open_tag_end = index_html.find('>', grid_start) + 1
            new_index = index_html[:open_tag_end] + '\n' + card + index_html[open_tag_end:]
            with open(index_path, 'w', encoding='utf-8') as f:
              f.write(new_index)
            print('Inserted vehicle card at top of featured inventory in index.html')
          else:
            print('No suitable insertion point in index.html; skipped index update')

if __name__ == '__main__':
    main()
