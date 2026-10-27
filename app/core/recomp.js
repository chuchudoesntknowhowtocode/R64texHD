'use strict';
// Recomp mod info for .rtz texture packs (Zelda 64: Recompiled and other N64ModernRuntime recomps).
//
// An .rtz may carry a mod.json (only display fields: .rtz files can't hold code) and a thumb.png.
// Without one, Recomp names the pack after its file. Rules from N64ModernRuntime's mod_manifest.cpp:
// required game_id, id, display_name, version, authors, minimum_recomp_version; optional
// description, short_description, enabled_by_default, config_schema. The texture pack on / off
// switch is an Enum option with id "_recomp_texture_pack_enabled" and exactly two options
// (first = off, second = on), from Zelda64Recomp's rt64_render_context.cpp.

const MANIFEST = 'mod.json';
const THUMB = 'thumb.png';
const TOGGLE_ID = '_recomp_texture_pack_enabled';
const MIN_RECOMP = '1.2.0';                       // first Zelda 64: Recompiled with .rtz support
const VERSION_RE = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/;

// "Majora HD Reimagined" -> "majora_hd_reimagined"
const modId = (name) => (String(name || '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '') || 'texture_pack');

// opts: { name, author, version, description, game, toggle }
function manifest(opts) {
  const name = String(opts.name || '').trim() || 'HD Texture Pack';
  const version = String(opts.version || '').trim() || '1.0.0';
  if (!VERSION_RE.test(version)) throw new Error(`Recomp needs a version like 1.0.0 (got “${version}”).`);
  const authors = String(opts.author || '').split(/\s*[,;&]\s*/).map((a) => a.trim()).filter(Boolean);
  const m = {
    game_id: String(opts.game || 'mm').trim() || 'mm',
    id: modId(opts.id || name),
    display_name: name,
    version,
    authors: authors.length ? authors : ['Unknown'],
    minimum_recomp_version: MIN_RECOMP,
  };
  const desc = String(opts.description || '').trim();
  if (desc) { m.description = desc; m.short_description = desc.length > 80 ? desc.slice(0, 77) + '…' : desc; }
  if (opts.toggle !== false) {
    m.config_schema = { options: [{ id: TOGGLE_ID, name: 'HD textures', description: 'Turn this texture pack on or off.', type: 'Enum', options: ['Off', 'On'], default: 'On' }] };
  }
  return m;
}

// Checks a mod.json the same way Recomp does. Returns { ok, problems: [], info }.
function validate(text) {
  let j;
  try { j = JSON.parse(String(text).replace(/^﻿/, '')); } catch { return { ok: false, problems: ['mod.json is not valid JSON'] }; }
  if (!j || typeof j !== 'object' || Array.isArray(j)) return { ok: false, problems: ['mod.json must be a JSON object'] };
  const problems = [];
  for (const k of ['game_id', 'id', 'display_name', 'version', 'minimum_recomp_version']) if (typeof j[k] !== 'string' || !j[k]) problems.push(`missing ${k}`);
  if (!Array.isArray(j.authors) || !j.authors.every((a) => typeof a === 'string')) problems.push('authors must be a list of names');
  for (const k of ['version', 'minimum_recomp_version']) if (typeof j[k] === 'string' && !VERSION_RE.test(j[k])) problems.push(`${k} “${j[k]}” is not like 1.0.0`);
  const opt = j.config_schema && Array.isArray(j.config_schema.options) ? j.config_schema.options.find((o) => o && o.id === TOGGLE_ID) : null;
  if (opt && (opt.type !== 'Enum' || !Array.isArray(opt.options) || opt.options.length !== 2)) problems.push('the on / off switch must be an Enum with exactly two options');
  return { ok: !problems.length, problems, info: { name: j.display_name, version: j.version, authors: j.authors, game: j.game_id, toggle: !!opt } };
}

module.exports = { MANIFEST, THUMB, TOGGLE_ID, MIN_RECOMP, manifest, validate, modId };
