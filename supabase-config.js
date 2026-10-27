// Public Supabase browser configuration.
// The publishable key is designed for public clients; RLS must protect every exposed table.
// NEVER put a service_role or sb_secret key in this file or in a browser bundle.
window.MULTY_SUPABASE_CONFIG = Object.freeze({
  url: "https://abxapmbiuijaybwddvrw.supabase.co",
  publishableKey: "sb_publishable_ONBGnBrmoG4Q_gTpVVQejA_AMw53mm_",
  // Use the deployed app URL, never the origin that happened to serve the signup form.
  emailRedirectTo: "https://bdssmdkacem-dot.github.io/Multy/auth.html"
});
