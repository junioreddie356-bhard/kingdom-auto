function formatPrice(value){
  if (value === undefined || value === null) return 'Contact for pricing';
  const str = String(value).trim();
  if (!/\d/.test(str)) return str || 'Contact for pricing';
  const num = Number(str.replace(/[^0-9.-]+/g, ''));
  if (isNaN(num)) return str;
  try{
    // Use Unicode escape for cedi symbol to avoid encoding issues
    return 'GH\u20B5' + num.toLocaleString('en-US');
  }catch(e){
    return 'GH\u20B5' + num;
  }
}

// expose for older browsers
window.formatPrice = formatPrice;
