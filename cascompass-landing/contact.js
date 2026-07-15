(() => {
  'use strict';

  const ticketEndpoint = 'https://cas-harness-customer-api.onrender.com/api/support/public/tickets';
  const noticeEndpoint = 'https://cas-harness-customer-api.onrender.com/api/support/public/privacy-notice';
  const expectedNoticeUrl = 'https://cascompass.ai/privacy';
  const noticeVersionPattern = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
  const noticeDigestPattern = /^[0-9a-f]{64}$/;
  const form = document.getElementById('support-form');
  const status = document.getElementById('support-status');
  if (!(form instanceof HTMLFormElement) || !(status instanceof HTMLElement)) return;

  function parsePublishedNotice(body) {
    if (!body || typeof body !== 'object' || Array.isArray(body)) {
      throw new Error('The published Privacy Notice metadata is malformed.');
    }
    const expectedKeys = [
      'privacy_notice_content_sha256',
      'privacy_notice_publication_status',
      'privacy_notice_version',
      'privacy_url',
    ];
    const actualKeys = Object.keys(body).sort();
    if (JSON.stringify(actualKeys) !== JSON.stringify(expectedKeys)) {
      throw new Error('The published Privacy Notice metadata is malformed.');
    }
    if (
      body.privacy_url !== expectedNoticeUrl
      || body.privacy_notice_publication_status !== 'present'
      || typeof body.privacy_notice_version !== 'string'
      || !noticeVersionPattern.test(body.privacy_notice_version)
      || typeof body.privacy_notice_content_sha256 !== 'string'
      || !noticeDigestPattern.test(body.privacy_notice_content_sha256)
    ) {
      throw new Error('The published Privacy Notice metadata is unavailable.');
    }
    return body;
  }

  async function fetchPublishedNotice() {
    const response = await fetch(noticeEndpoint, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      cache: 'no-store',
      credentials: 'omit',
      redirect: 'error',
      referrerPolicy: 'no-referrer',
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = typeof body.detail === 'string'
        ? body.detail
        : 'The published Privacy Notice metadata is unavailable.';
      throw new Error(detail);
    }
    const contentType = String(response.headers.get('Content-Type') || '')
      .split(';', 1)[0]
      .trim()
      .toLowerCase();
    const cacheControl = String(response.headers.get('Cache-Control') || '')
      .split(',')
      .map((value) => value.trim().toLowerCase());
    if (contentType !== 'application/json' || !cacheControl.includes('no-store')) {
      throw new Error('The published Privacy Notice metadata is malformed.');
    }
    return parsePublishedNotice(body);
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;

    const submit = form.querySelector('button[type="submit"]');
    if (submit instanceof HTMLButtonElement) submit.disabled = true;
    status.textContent = 'Checking the current published Privacy Notice\u2026';

    try {
      // Resolve the notice immediately before every submission. No legal
      // version or digest is baked into the landing bundle or retained across
      // attempts; an OPEN, invalid, unavailable, or changed notice blocks PII.
      const notice = await fetchPublishedNotice();
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
        privacy_notice_version: notice.privacy_notice_version,
        privacy_notice_content_sha256: notice.privacy_notice_content_sha256,
      };
      status.textContent = 'Submitting your support request\u2026';
      const response = await fetch(ticketEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        cache: 'no-store',
        credentials: 'omit',
        redirect: 'error',
        referrerPolicy: 'no-referrer',
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
