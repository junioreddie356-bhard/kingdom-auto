document.addEventListener('DOMContentLoaded', function(){
  function parseNumericPrice(str){
    if(!str) return null;
    // remove currency symbol and non-number characters except dot and comma
    const cleaned = str.replace(/[^0-9.,]/g, '').replace(/,/g,'');
    const n = parseFloat(cleaned);
    return Number.isFinite(n) ? n : null;
  }

  function fmt(n){
    return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }

  document.querySelectorAll('.price').forEach(el => {
    try{
      // preserve link if present
      const link = el.querySelector('a');
      const raw = el.textContent || '';
      const num = parseNumericPrice(raw);
      if(!num) return;
      const low = Math.round((num * 0.9) / 100) * 100; // -10%, rounded to 100
      const high = Math.round((num * 1.1) / 100) * 100; // +10%
      const rangeText = `GH₵${fmt(low)} - GH₵${fmt(high)}`;
      if(link){
        el.innerHTML = rangeText + ' ' + link.outerHTML;
      } else {
        el.textContent = rangeText;
      }
    }catch(e){/* no-op */}
  });
});
