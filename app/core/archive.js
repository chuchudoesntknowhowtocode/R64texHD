'use strict';
// One way to read a Ship port archive, whichever kind it is: .o2r (zip) or the older .otr (MPQ).
const rtz = require('./rtz');
const mpq = require('./mpq');

const entries = (file) => (mpq.isMpq(file) ? mpq.readEntries(file) : rtz.readEntries(file));
const read = (file, e, fd) => (e.mpq ? mpq.readEntry(file, e, fd) : rtz.readEntry(file, e, fd));

module.exports = { entries, read, isMpq: mpq.isMpq };
