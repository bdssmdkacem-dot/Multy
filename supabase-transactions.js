(() => {
  'use strict';
  const config = window.MULTY_SUPABASE_CONFIG;
  if (!window.supabase || !config) return;

  const $ = selector => document.querySelector(selector);
  const client = window.supabase.createClient(config.url, config.publishableKey, {
    auth: { autoRefreshToken: true, persistSession: true, detectSessionInUrl: true }
  });
  let connected = false;
  let companyId = null;
  let transactions = [];

  function toast(message) {
    const node = $('#toast');
    node.textContent = message;
    node.classList.add('show');
    setTimeout(() => node.classList.remove('show'), 3200);
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, character => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[character]);
  }

  function formatMoney(value) {
    return new Intl.NumberFormat('fr-MA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      .format(Math.abs(Number(value) || 0)) + ' DH';
  }

  function formatDate(value) {
    return new Intl.DateTimeFormat('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' })
      .format(new Date(value + 'T12:00:00'));
  }

  function localDate() {
    const now = new Date();
    return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  }

  function renderTable() {
    const body = $('#transactionRows');
    body.innerHTML = transactions.map(transaction => {
      const amount = Number(transaction.amount);
      const isIncome = amount >= 0;
      const description = escapeHtml(transaction.description);
      return `<tr data-search="${description} ${escapeHtml(transaction.category)}">
        <td><div class="transaction-name"><div class="merchant-icon">${escapeHtml(transaction.description.slice(0, 1).toLocaleUpperCase('fr'))}</div><div><strong>${description}</strong><span>Saisie manuelle · MAD</span></div></div></td>
        <td>${formatDate(transaction.occurred_on)}</td><td>${escapeHtml(transaction.category)}</td>
        <td><span class="status paid">Enregistrée</span></td>
        <td class="amount ${isIncome ? 'positive' : ''}">${isIncome ? '+' : '−'}${formatMoney(amount)}</td>
      </tr>`;
    }).join('');
    $('#emptyState').style.display = transactions.length ? 'none' : 'block';
    $('#emptyState').textContent = 'Aucune transaction ne correspond à votre recherche.';
    $('#search').dispatchEvent(new Event('input', { bubbles: true }));
    renderTransactionsModule();
  }

  function renderTransactionsModule() {
    if (!$('#modulePage').classList.contains('active') || $('#crumb').textContent !== 'Transactions') return;
    const banner = $('#modulePage .module-banner');
    if (banner) banner.textContent = 'Transactions enregistrées dans Supabase. Elles sont saisies manuellement; aucune banque n’est connectée.';
    const rows = $('#moduleRows');
    if (!rows) return;
    rows.replaceChildren();
    for (const transaction of transactions) {
      const row = document.createElement('tr');
      row.dataset.kind = Number(transaction.amount) >= 0 ? 'income' : 'expense';
      row.dataset.status = 'recorded';
      for (const value of [transaction.description, formatDate(transaction.occurred_on), transaction.category, 'Enregistrée',
        (Number(transaction.amount) >= 0 ? '+' : '−') + formatMoney(transaction.amount)]) {
        const cell = document.createElement('td');
        cell.textContent = value;
        row.append(cell);
      }
      rows.append(row);
    }
  }

  async function loadTransactions() {
    const { data, error } = await client.from('transactions')
      .select('id,description,amount,currency,category,occurred_on')
      .eq('company_id', companyId)
      .order('occurred_on', { ascending: false })
      .limit(200);
    if (error) throw error;
    transactions = data || [];
    renderTable();
  }

  async function start() {
    const { data: { session }, error } = await client.auth.getSession();
    if (error) throw error;
    if (!session) {
      $('#accountLink').hidden = false;
      return;
    }

    connected = true;
    $('#accountLink').hidden = true;
    $('#signOut').hidden = false;
    const { data: memberships, error: membershipError } = await client.from('firm_members')
      .select('firm_id,role').limit(1);
    if (membershipError) throw membershipError;
    if (!memberships?.length) {
      location.href = './auth.html';
      return;
    }
    const { data: companies, error: companyError } = await client.from('companies')
      .select('id,name').eq('firm_id', memberships[0].firm_id);
    if (companyError) throw companyError;
    if (!companies?.length) {
      $('#transactionRows').replaceChildren();
      $('#emptyState').style.display = 'block';
      $('#emptyState').textContent = 'Créez une entreprise dans Facturation avant d’ajouter des opérations.';
      $('#newBtn').disabled = true;
      $('#transactionsNotice').hidden = false;
      $('#transactionsNotice').textContent = 'Espace connecté. Ouvrez Facturation pour créer votre première entreprise.';
      $('#transactionsNotice').insertAdjacentHTML('beforeend', ' <a href="./facturation.html">Ouvrir Facturation</a>');
      $('#storageState').textContent = 'Connecté · aucune entreprise configurée';
      return;
    }

    companyId = companies[0].id;
    $('.workspace strong').firstChild.textContent = companies[0].name;
    $('#transactionsNotice').hidden = false;
    $('#transactionsNotice').textContent = 'Les transactions sont synchronisées avec Supabase. Les indicateurs, prévisions et autres modules restent des exemples; aucune banque n’est connectée.';
    $('#storageState').textContent = 'Transactions sauvegardées dans Supabase · autres indicateurs en démo';
    await loadTransactions();
  }

  $('#newBtn').addEventListener('click', async event => {
    if (!connected) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    if (!companyId) {
      toast('Créez une entreprise dans Facturation avant de continuer.');
      return;
    }
    const description = prompt('Libellé de l’opération');
    if (!description?.trim()) return;
    if (description.trim().length > 240) {
      toast('Le libellé ne peut pas dépasser 240 caractères.');
      return;
    }
    const rawAmount = prompt('Montant en DH : positif pour une entrée, négatif pour une sortie');
    if (rawAmount === null || !rawAmount.trim()) return;
    const amount = Number(rawAmount.trim().replace(',', '.'));
    if (!Number.isFinite(amount) || amount === 0 || Math.abs(amount) >= 1000000000) {
      toast('Saisissez un montant valide, différent de zéro.');
      return;
    }
    const category = prompt('Catégorie (ex. Prestations, Logiciels, Locaux)', 'Divers') || 'Divers';
    if (category.trim().length > 80) {
      toast('La catégorie ne peut pas dépasser 80 caractères.');
      return;
    }
    const { error } = await client.from('transactions').insert({
      company_id: companyId,
      description: description.trim(),
      amount,
      currency: 'MAD',
      category: category.trim() || 'Divers',
      occurred_on: localDate()
    });
    if (error) {
      toast('Enregistrement refusé : ' + String(error.message || error).slice(0, 180));
      return;
    }
    await loadTransactions();
    toast('Transaction enregistrée dans Supabase.');
  }, true);

  $('#signOut').addEventListener('click', async () => {
    const { error } = await client.auth.signOut();
    if (error) {
      toast('Déconnexion impossible : ' + error.message);
      return;
    }
    location.href = './auth.html';
  });

  document.querySelectorAll('.nav button[data-page="Transactions"]').forEach(button => {
    button.addEventListener('click', () => setTimeout(renderTransactionsModule, 0), true);
  });

  start().catch(error => {
    $('#transactionsNotice').hidden = false;
    $('#transactionsNotice').textContent = 'Impossible de charger les transactions : ' + String(error.message || error).slice(0, 180) + ' · Vérifiez que les migrations sont appliquées.';
    $('#storageState').textContent = 'Connexion indisponible';
    $('#accountLink').hidden = connected;
    $('#transactionRows').replaceChildren();
    $('#emptyState').style.display = 'block';
    $('#emptyState').textContent = 'Les transactions n’ont pas pu être chargées.';
  });
})();
