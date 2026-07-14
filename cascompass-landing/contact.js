(() => {
  'use strict';

  const endpoint = 'https://noetic-compass-api.onrender.com/api/support/public/tickets';
  const form = document.getElementById('support-form');
  const status = document.getElementById('support-status');
  if (!(form instanceof HTMLFormElement) || !(status instanceof HTMLElement)) return;

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;

    const submit = form.querySelector('button[type="submit"]');
    if (submit instanceof HTMLButtonElement) submit.disabled = true;
    status.textContent = 'Submitting your support request\u2026';

    const data = new FormData(form);
    const payload = {
      email: String(data.get('email') || ''),
      name: String(data.get('name') || ''),
      organization: String(data.get('organization') || ''),
      category: String(data.get('category') || 'product_support'),
      subject: String(data.get('subject') || ''),
      message: String(data.get('message') || ''),
      website: String(data.get('website') || ''),
      source: 'cascompass_contact',
      consent_to_contact: data.get('consent_to_contact') === 'on',
    };

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = typeof body.detail === 'string' ? body.detail : 'The request could not be recorded.';
        throw new Error(detail);
      }
      status.textContent = `Request received. Ticket ID: ${String(body.ticket_id || 'unavailable')}.`;
      form.reset();
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Unknown error';
      status.textContent = `Support intake is temporarily unavailable: ${detail} Use the email fallback below.`;
    } finally {
      if (submit instanceof HTMLButtonElement) submit.disabled = false;
    }
  });
})();
