document.addEventListener('DOMContentLoaded', function(){
  const supabaseApi = window.KingdomSupabase;

  function isEmail(v){return /\S+@\S+\.\S+/.test(v)}
  function isPhone(v){return /^\+?\d{7,15}$/.test(v.replace(/\s+/g,''))}
  function validContact(v){return isEmail(v) || isPhone(v)}
  function isStrongPassword(p){
    if(!p || p.length < 8) return false;
    if(!/[A-Z]/.test(p)) return false;
    if(!/[0-9]/.test(p)) return false;
    if(!/[!@#\$%\^&\*(),.?":{}|<>\[\]\\;\/'`~\-+=]/.test(p)) return false;
    return true;
  }
  function showError(el,msg){
    let err = el.parentNode.querySelector('.error');
    if(!err){ err = document.createElement('div'); err.className='error'; el.parentNode.appendChild(err); }
    err.textContent = msg;
  }
  function clearError(el){
    const err = el.parentNode.querySelector('.error'); if(err) err.textContent='';
  }

  const signupForm = document.getElementById('signup-form');
  if(signupForm){
    const first = signupForm.querySelector('input[name="first_name"]');
    const middle = signupForm.querySelector('input[name="middle_name"]');
    const last = signupForm.querySelector('input[name="last_name"]');
    const email = signupForm.querySelector('input[name="email"]');
    const phone = signupForm.querySelector('input[name="phone"]');
    const password = signupForm.querySelector('input[name="password"]');
    const confirm = signupForm.querySelector('input[name="confirm_password"]');

    [first,middle,last,email,phone,password,confirm].forEach(i=>i&&i.addEventListener('input', ()=>clearError(i)));

    signupForm.addEventListener('submit', async function(e){
      e.preventDefault();
      let ok = true;
      if(!first.value.trim()){ showError(first,'Enter your first name'); ok=false }
      if(!last.value.trim()){ showError(last,'Enter your last name'); ok=false }
      if(!isEmail(email.value.trim())){ showError(email,'Enter a valid email address'); ok=false }
      if(!isPhone(phone.value.trim())){ showError(phone,'Enter a valid phone number'); ok=false }
      if(!isStrongPassword(password.value)){ showError(password,'Password must be at least 8 characters and include an uppercase letter, a number, and a symbol'); ok=false }
      if(password.value !== confirm.value){ showError(confirm,'Passwords do not match'); ok=false }
      if(!ok) return;

      if (supabaseApi && supabaseApi.isConfigured) {
        const { error } = await supabaseApi.signUpCustomer({
          email: email.value.trim(),
          password: password.value,
          metadata: {
            first_name: first.value.trim(),
            middle_name: (middle && middle.value.trim()) || '',
            last_name: last.value.trim(),
            phone: phone.value.trim(),
            source: 'kingdom-automobile'
          }
        });

        if (error) {
          showError(email, error.message || 'Unable to create account.');
          return;
        }

        alert('Account created. Check your email to verify your account, then sign in.');
        window.location.href = 'login.html';
        return;
      }

      alert('Account created. Redirecting to login.');
      window.location.href = 'login.html';
    });
  }

  // Show/hide password toggles
  document.querySelectorAll('.toggle-password').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const targetName = btn.getAttribute('data-target');
      const form = btn.closest('form') || document;
      const input = form.querySelector(`[name="${targetName}"]`);
      if(!input) return;
      if(input.type === 'password'){
        input.type = 'text';
        btn.textContent = 'Hide';
      } else {
        input.type = 'password';
        btn.textContent = 'Show';
      }
    });
  });

  const loginForm = document.getElementById('login-form');
  if(loginForm){
    const contact = loginForm.querySelector('input[name="contact"]');
    const password = loginForm.querySelector('input[name="password"]');
    [contact,password].forEach(i=>i&&i.addEventListener('input', ()=>clearError(i)));
    loginForm.addEventListener('submit', async function(e){
      e.preventDefault();
      let ok = true;
      if(!validContact(contact.value.trim())){ showError(contact,'Enter a valid email or phone number'); ok=false }
      if(password.value.trim().length === 0){ showError(password,'Enter your password'); ok=false }
      if(!ok) return;

      if (supabaseApi && supabaseApi.isConfigured) {
        const { error } = await supabaseApi.signInCustomer({
          contact: contact.value.trim(),
          password: password.value
        });

        if (error) {
          showError(contact, error.message || 'Unable to sign in.');
          return;
        }

        alert('Logged in successfully. Redirecting to home.');
        window.location.href = 'index.html';
        return;
      }

      alert('Logged in successfully. Redirecting to home.');
      window.location.href = 'index.html';
    });
  }
});
