// Fonction "podcast" : API du site web + bot Telegram (Supabase Edge Function)
const SB_URL = Deno.env.get("SUPABASE_URL") ?? "";
let SB_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
try { SB_KEY = JSON.parse(Deno.env.get("SUPABASE_SECRET_KEYS") ?? "{}")["default"] ?? SB_KEY; } catch (_e) { /* on garde l'ancienne clé */ }
const GROQ = Deno.env.get("GROQ_API_KEY") ?? "";
const TG = Deno.env.get("TELEGRAM_BOT_TOKEN") ?? "";
const CODE = Deno.env.get("SITE_CODE") ?? "";
const WEBHOOK_SECRET = Deno.env.get("TELEGRAM_WEBHOOK_SECRET") ?? "";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, x-site-code",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const json = (o: unknown, status = 200) =>
  new Response(JSON.stringify(o), { status, headers: { ...CORS, "Content-Type": "application/json" } });

// ---------- Supabase
async function sb(path: string, init: any = {}) {
  const headers: Record<string, string> = { apikey: SB_KEY, "Content-Type": "application/json", ...(init.headers ?? {}) };
  if (SB_KEY.startsWith("eyJ")) headers.Authorization = `Bearer ${SB_KEY}`;
  const r = await fetch(`${SB_URL}/rest/v1/${path}`, { ...init, headers });
  if (!r.ok) throw new Error(`Supabase ${r.status} : ${(await r.text()).slice(0, 200)}`);
  const t = await r.text();
  return t ? JSON.parse(t) : null;
}
const rpc = (fn: string, args: Record<string, unknown>) => sb(`rpc/${fn}`, { method: "POST", body: JSON.stringify(args) });

// ---------- IA (Groq)
async function llm(prompt: string, jsonMode = false, max = 1800): Promise<string> {
  if (!GROQ) throw new Error("La clé GROQ_API_KEY est absente des Secrets Supabase.");
  const erreurs: string[] = [];
  const candidats = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"];
  let recherche = false;
  for (let i = 0; i < candidats.length; i++) {
    const model = candidats[i];
    const r = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: { Authorization: `Bearer ${GROQ}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        model, temperature: 0.3, max_tokens: max + 2000,
        ...(model.includes("gpt-oss") ? { reasoning_effort: "low" } : {}),
        messages: [{ role: "user", content: prompt }],
        ...(jsonMode ? { response_format: { type: "json_object" } } : {}),
      }),
    });
    if (r.ok) {
      const contenu = (await r.json()).choices?.[0]?.message?.content as string | undefined;
      if (contenu) return contenu;
      erreurs.push(`${model} : réponse vide`);
    } else {
      erreurs.push(`${model} : HTTP ${r.status} ${(await r.text()).slice(0, 150)}`);
    }
    if (i === candidats.length - 1 && !recherche) { // les deux modèles échouent : on cherche un modèle disponible
      recherche = true;
      try {
        const m = await fetch("https://api.groq.com/openai/v1/models", { headers: { Authorization: `Bearer ${GROQ}` } });
        const exclus = ["whisper", "orpheus", "guard", "safeguard", "tts", "allam", "embed", "playai", "compound"];
        const taille = (id: string) => parseFloat(id.toLowerCase().match(/(\d+(?:\.\d+)?)b/)?.[1] ?? "0");
        const autres = ((await m.json()).data ?? []).map((x: any) => x.id as string)
          .filter((id: string) => !candidats.includes(id) && !exclus.some((x) => id.toLowerCase().includes(x)))
          .sort((a: string, b: string) => taille(b) - taille(a)).slice(0, 3);
        candidats.push(...autres);
      } catch (_e) { /* on ignore */ }
    }
  }
  throw new Error("IA indisponible. " + erreurs.join(" || "));
}
function lireJson(s: string, secours: any) { try { return JSON.parse(s); } catch (_e) { return secours; } }

// ---------- Fiches
const STYLE = "Style : puces courtes (une idée par ligne, 20 mots maximum), en français, niveau Bac/Bac+3, termes techniques expliqués en quelques mots. N'invente aucun chiffre ni aucun fait : utilise uniquement la matière fournie. Si elle est insuffisante, dis-le dans a_retenir.";

async function fiche(q: string, mode: string) {
  q = q.trim().slice(0, 200);
  if (!q) return { titre: "Question vide" };
  if (mode === "references") {
    const docs = await rpc("chercher_docs", { q, n: 10 });
    if (!docs.length) return { titre: q, a_retenir: "Aucun passage trouvé dans la RNS et la LPM. Essaie d'autres mots-clés." };
    const matiere = docs.map((d: any) => `- (${d.doc}, p. ${d.page}) ${d.content}`).join("\n");
    const prompt = `Tu prépares une fiche de synthèse pour un candidat en préparation du grand oral de fin de scolarité (filière gestion-économie, option finance). Mot-clé : « ${q} ». Matière : extraits de la Revue nationale stratégique 2025 (RNS) et de la loi de programmation militaire 2024-2030 (LPM).\n${STYLE}\nRÈGLES : synthétise ce que disent les documents sur ce mot-clé, sans recopier les extraits. Indique le document et la page entre parenthèses pour chaque information (ex. (LPM, p. 12)). Ne mélange pas la RNS et la LPM sans le dire. Ignore les extraits qui parlent d'autre chose.\n\nEXTRAITS :\n${matiere}\n\nRéponds uniquement en JSON : {"titre":"","definition":["ce que recouvre le mot-clé, 2 à 3 puces"],"ce_que_disent_les_documents":["puces avec (document, page)"],"chiffres":["valeur — description (document, page)"],"enjeux":[],"a_retenir":"2 phrases","questions_liees":["3 à 5 questions"]}`;
    const f = lireJson(await llm(prompt, true, 2000), { titre: q, a_retenir: "Réponse illisible, réessaie." });
    f.extraits = docs.slice(0, 6).map((d: any) => ({ doc: d.doc, page: d.page, content: d.content }));
    return f;
  }
  if (mode === "sources") {
    const [arts, docs] = await Promise.all([rpc("chercher_articles", { q, n: 12 }), rpc("chercher_docs", { q, n: 4 })]);
    if (!arts.length && !docs.length) return { titre: q, a_retenir: "Rien trouvé dans les sources collectées. Essaie d'autres mots-clés." };
    const matiere = arts.map((a: any) => `- [${a.source}, publié le ${String(a.published).slice(0, 10)}] ${a.title}. ${a.summary ?? ""}`).join("\n")
      + "\n\nDOCUMENTS DE RÉFÉRENCE :\n" + docs.map((d: any) => `- (${d.doc}, p. ${d.page}) ${d.content}`).join("\n");
    const prompt = `Tu prépares une fiche de synthèse pour un candidat en préparation du grand oral de fin de scolarité (filière gestion-économie). Sujet : « ${q} ».\n${STYLE}\nRÈGLES : cite la source ET la date de publication de chaque information (ex. « Selon le ministère des Armées, publié le 03/10 »). Si deux informations se contredisent ou évoluent, garde la plus récente et mentionne l'évolution. Signale toute information de plus de 6 mois. Relie au RNS 2025 et à la LPM 2024-2030 quand les documents de référence s'y prêtent.\n\nMATIÈRE :\n${matiere}\n\nRéponds uniquement en JSON : {"titre":"","definition":[],"situation":[],"contexte_strategique":[],"acteurs":[],"enjeux":[],"chiffres":["valeur — description (date)"],"debat":[],"questions_liees":["3 à 5 questions"]}`;
    const f = lireJson(await llm(prompt, true, 2200), { titre: q, a_retenir: "Réponse illisible, réessaie." });
    f.liens = arts.slice(0, 8).map((a: any) => ({ source: a.source, title: a.title, link: a.link }));
    return f;
  }
  const rows = await rpc("chercher_sujets", { q, n: 6 });
  if (!rows.length) return { titre: q, a_retenir: "Ce sujet n'a pas encore été traité dans tes podcasts. Essaie le mode Sources." };
  const matiere = rows.map((r: any) => `${r.nom} : ${r.texte}\nÀ retenir : ${r.a_retenir}\nChiffres : ${(r.chiffres ?? []).join(" ; ")}`).join("\n\n").slice(0, 9000);
  const prompt = `Tu résumes à un élève ce qu'il a déjà entendu dans ses podcasts sur « ${q} », comme un camarade qui lui récapitule le cours.\n${STYLE}\nRÈGLES : ne cite aucun média, aucune date, aucun numéro de podcast.\n\nMATIÈRE :\n${matiere}\n\nRéponds uniquement en JSON : {"titre":"","sujet":["3 à 5 puces"],"enjeux":[],"chiffres":["valeur — description (3 à 7)"],"a_retenir":"2 phrases","questions_liees":["3 à 5 questions"]}`;
  return lireJson(await llm(prompt, true, 1800), { titre: q, a_retenir: "Réponse illisible, réessaie." });
}

const SECTIONS: [string, string][] = [
  ["sujet", "LE SUJET"], ["definition", "DÉFINITION & CADRE"], ["ce_que_disent_les_documents", "CE QUE DISENT LES DOCUMENTS"], ["situation", "SITUATION ACTUELLE"],
  ["contexte_strategique", "CONTEXTE STRATÉGIQUE"], ["acteurs", "ACTEURS"], ["enjeux", "LES ENJEUX"],
  ["chiffres", "CHIFFRES CLÉS"], ["debat", "POINTS DE DÉBAT"], ["a_retenir", "À RETENIR"], ["questions_liees", "QUESTIONS LIÉES"],
];
function ficheTexte(f: any): string {
  const out: string[] = [`📌 ${f.titre ?? ""}`];
  for (const [k, titre] of SECTIONS) {
    const v = f[k];
    if (Array.isArray(v) && v.length) out.push(`${titre}\n` + v.map((x: unknown) => `• ${x}`).join("\n"));
    else if (typeof v === "string" && v) out.push(`${titre}\n${v}`);
  }
  if (f.liens?.length) out.push("SOURCES\n" + f.liens.map((l: any) => `• ${l.source} : ${l.link}`).join("\n"));
  return out.join("\n\n");
}

// ---------- Bot Telegram
const AIDE = "Bot de préparation au grand oral.\n• Écris un mot-clé ou une question (ou envoie un vocal) : fiche tirée de tes podcasts.\n• /sources mot : fiche approfondie avec sources et dates.\n• /examen : examen blanc.\n• Réponds au message « Question du jour » pour recevoir un retour.";
const tg = (methode: string, corps: unknown) =>
  fetch(`https://api.telegram.org/bot${TG}/${methode}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corps) });
async function dire(chat: number, texte: string) {
  for (let i = 0; i < texte.length; i += 4000) await tg("sendMessage", { chat_id: chat, text: texte.slice(i, i + 4000) });
}
async function transcrire(fileId: string): Promise<string> {
  const info = await (await tg("getFile", { file_id: fileId })).json();
  const audio = await fetch(`https://api.telegram.org/file/bot${TG}/${info.result.file_path}`);
  const form = new FormData();
  form.append("file", new File([await audio.blob()], "vocal.ogg", { type: "audio/ogg" }));
  form.append("model", "whisper-large-v3-turbo");
  form.append("language", "fr");
  const r = await fetch("https://api.groq.com/openai/v1/audio/transcriptions", { method: "POST", headers: { Authorization: `Bearer ${GROQ}` }, body: form });
  if (!r.ok) throw new Error("Transcription impossible (limite gratuite atteinte ?)");
  return (await r.json()).text as string;
}
async function matiereDe(q: string): Promise<string> {
  const [rows, docs] = await Promise.all([rpc("chercher_sujets", { q, n: 4 }), rpc("chercher_docs", { q, n: 3 })]);
  return (rows.map((r: any) => `${r.nom} : ${r.texte} Chiffres : ${(r.chiffres ?? []).join(" ; ")}`).join("\n")
    + "\n" + docs.map((d: any) => `(${d.doc}, p. ${d.page}) ${d.content}`).join("\n")).slice(0, 8000) || "(aucune)";
}
async function examenDebut(chat: number) {
  const depuis = new Date(Date.now() - 7 * 86400000).toISOString().slice(0, 10);
  const rows = await sb(`podcast_topics?date=gte.${depuis}&select=nom&order=date.desc&limit=40`);
  const noms = [...new Set(rows.map((r: any) => r.nom as string))].sort(() => Math.random() - 0.5).slice(0, 3);
  if (!noms.length) { await dire(chat, "Pas encore assez de podcasts en mémoire."); return; }
  await dire(chat, "🎓 Examen blanc : 3 sujets tirés de ta semaine. Choisis-en un et prépare-toi 10 minutes. Puis réponds AU MESSAGE du sujet choisi (appui long > Répondre) avec un vocal de 3 à 5 minutes.");
  for (const n of noms) await dire(chat, `🎓 EXAMEN BLANC — Sujet : ${n}`);
}
async function examenRetour(chat: number, rep: string, expose: string, vocal: boolean) {
  const sujet = rep.split("Sujet :")[1]?.trim() ?? rep;
  const prompt = `Tu es un jury de grand oral de fin de scolarité (filière gestion-économie, option finance). Le candidat vient de présenter le sujet « ${sujet} »${vocal ? " (transcription d'un vocal : ignore les erreurs de transcription)" : ""}.\n\nEXPOSÉ DU CANDIDAT :\n${expose}\n\nMATIÈRE DE RÉFÉRENCE (pour vérifier faits et chiffres) :\n${await matiereDe(sujet)}\n\nRéponds en français, en texte simple (sans markdown) :\n1) Cinq questions de jury, de la plus simple à la plus piégeuse.\n2) Un retour structuré : Clarté (transitions utilisées ?), Précision (chiffres exacts, erreurs repérées), Profondeur (mécanismes expliqués ?), Ce qui manque.\n3) Une note indicative sur 20.\nSois exigeant mais bienveillant. N'invente aucun fait.`;
  await dire(chat, await llm(prompt, false, 1800));
}
async function questionRetour(chat: number, rep: string, reponse: string) {
  const q = rep.replace("❓ Question du jour :", "").split("\n")[0].trim();
  const prompt = `Question posée au candidat (grand oral de fin de scolarité, filière gestion-économie) : « ${q} »\nRéponse du candidat : ${reponse}\n\nMATIÈRE DE RÉFÉRENCE :\n${await matiereDe(q)}\n\nDonne un retour en 8 lignes maximum, en texte simple : ce qui est juste, ce qui manque ou est inexact (vérifie les chiffres avec la matière), puis une réponse modèle en 3 phrases. N'invente aucun fait.`;
  await dire(chat, await llm(prompt, false, 900));
}

async function bot(u: any) {
  const m = u.message;
  if (!m) return;
  const chat: number = m.chat.id;
  try {
    const texte: string = (m.text ?? "").trim();
    if (texte.startsWith("/start")) {
      if (!CODE || texte.split(/\s+/)[1] !== CODE) { await dire(chat, "Accès privé. Envoie : /start TON_CODE"); return; }
      await sb("utilisateurs?on_conflict=chat_id", { method: "POST", headers: { Prefer: "resolution=ignore-duplicates,return=minimal" }, body: JSON.stringify([{ chat_id: chat, nom: m.from?.first_name ?? "" }]) });
      await dire(chat, AIDE);
      return;
    }
    const connu = await sb(`utilisateurs?chat_id=eq.${chat}&select=chat_id`);
    if (!connu.length) { await dire(chat, "Accès privé. Envoie : /start TON_CODE"); return; }
    const rep: string = m.reply_to_message?.text ?? "";
    let saisie = texte;
    if (m.voice) { await dire(chat, "🎙️ Je transcris ton vocal…"); saisie = await transcrire(m.voice.file_id); }
    if (!saisie) return;
    if (rep.startsWith("🎓 EXAMEN BLANC")) { await examenRetour(chat, rep, saisie, !!m.voice); return; }
    if (rep.startsWith("❓ Question du jour")) { await questionRetour(chat, rep, saisie); return; }
    if (saisie.startsWith("/aide")) { await dire(chat, AIDE); return; }
    if (saisie.startsWith("/examen")) { await examenDebut(chat); return; }
    await dire(chat, "🔎 Je cherche…");
    if (saisie.startsWith("/sources")) await dire(chat, ficheTexte(await fiche(saisie.replace(/^\/sources(@\S+)?/, ""), "sources")));
    else await dire(chat, ficheTexte(await fiche(saisie, "podcasts")));
  } catch (e) {
    await dire(chat, "⚠️ " + ((e as Error).message ?? "erreur"));
  }
}

// ---------- Point d'entrée
Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  let body: any;
  try { body = await req.json(); } catch (_e) { return json({ error: "requête invalide" }, 400); }

  if (body.update_id !== undefined) { // message envoyé par Telegram
    if (WEBHOOK_SECRET && req.headers.get("x-telegram-bot-api-secret-token") !== WEBHOOK_SECRET) return new Response("interdit", { status: 403 });
    const tache = bot(body).catch((e) => console.error(e));
    const rt = (globalThis as any).EdgeRuntime;
    if (rt?.waitUntil) rt.waitUntil(tache); else await tache;
    return new Response("ok");
  }

  if (!CODE || req.headers.get("x-site-code") !== CODE) return json({ error: "Code d'accès incorrect" }, 401);
  try {
    switch (body.action) {
      case "podcasts": return json(await sb("podcast_topics?select=id,date,nom,domaine,a_retenir,chiffres,approfondi&order=date.desc,id.asc&limit=80"));
      case "sujet": return json((await sb(`podcast_topics?id=eq.${Number(body.id)}&select=*`))[0] ?? null);
      case "carte": return json(await sb("podcast_topics?select=nom,domaine,date&order=date.desc&limit=1000"));
      case "glossaire": return json(await sb("glossaire?select=terme,definition,domaine&order=terme.asc&limit=1000"));
      case "docs": return json(await rpc("chercher_docs", { q: String(body.q ?? ""), n: 8 }));
      case "fiche": return json(await fiche(String(body.q ?? ""), body.mode === "sources" ? "sources" : body.mode === "references" ? "references" : "podcasts"));
      default: return json({ error: "action inconnue" }, 400);
    }
  } catch (e) {
    return json({ error: (e as Error).message }, 500);
  }
});
