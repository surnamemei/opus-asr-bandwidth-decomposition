-- Pandoc Lua filter for tools/render_ieee.sh (IEEE journal layout; LaTeX only; presentation only).
--   1. The "Abstract" section and its "Index Terms" paragraph become IEEEtran's abstract and
--      IEEEkeywords environments.
--   2. Tables become \IEEEautotable floats and figures \IEEEautofigure floats (tools/ieee-header.tex),
--      which measure themselves and choose one- or two-column placement; long text columns may
--      wrap. A captioned table followed directly by uncaptioned tables is set as one float, as in
--      tools/tables.lua.
--   3. Every float's label, kind and plain-text caption is written to $IEEE_FLOATS_TSV for
--      tools/ieee_layout_report.py.
--   4. Level-1 sections named in $IEEE_DROP_SECTIONS and figures named in $IEEE_DROP_FIGURES are
--      omitted (what-if renderings only).
-- Nothing in the text, tables or figures is changed.
if not FORMAT:match("latex") then return {} end

local floats = {}

local function latex_of(blocks)
  local s = pandoc.write(pandoc.Pandoc(blocks), "latex")
  s = s:gsub("\n+$", ""):gsub("\n", " ")
  s = s:gsub("({%[}[^{]-),%s+([^{]-{%]})", "%1,~%2")   -- keep "[lo, hi]" on one line
  return s
end

local function plain(blocks)
  return (pandoc.utils.stringify(blocks):gsub("[\t\n]", " "))
end

local function rows_of(tbl)
  local rows = {}
  for _, r in ipairs(tbl.head.rows) do table.insert(rows, {head = true, cells = r.cells}) end
  for _, body in ipairs(tbl.bodies) do
    for _, r in ipairs(body.body) do table.insert(rows, {head = false, cells = r.cells}) end
  end
  return rows
end

local SHORT = 12   -- text columns up to this many characters are never wrapped

-- Column roles of one table: "wrap" (long text, type P{share}) or "fixed" (mostly numbers or
-- intervals, or short text; type l). Shares of the wrappable columns follow their longest cell.
local function roles(tbl)
  local rows, n = rows_of(tbl), #tbl.colspecs
  local maxlen, nnum, nvote, numeric = {}, {}, {}, {}
  for i = 1, n do maxlen[i], nnum[i], nvote[i] = 1, 0, 0 end
  for _, r in ipairs(rows) do
    for i, c in ipairs(r.cells) do
      local t = pandoc.utils.stringify(c.contents)
      local len = utf8.len(t) or #t
      if len > maxlen[i] then maxlen[i] = len end
      -- empty and dash-only placeholder cells do not vote
      if not r.head and t:match("%S") and not t:match("^[%s%-−–—]*$") then
        nvote[i] = nvote[i] + 1
        if t:match("%d") and t:match("^[%s%d%.,%[%]%+%-−—%%]*$") then nnum[i] = nnum[i] + 1 end
      end
    end
  end
  -- a column of mostly numbers or intervals is never wrapped (a stray "GO" does not change that)
  for i = 1, n do numeric[i] = nvote[i] > 0 and nnum[i] * 2 >= nvote[i] end
  local wrap, total = {}, 0
  for i = 1, n do
    wrap[i] = (not numeric[i]) and maxlen[i] > SHORT
    if wrap[i] then total = total + maxlen[i] end
  end
  local share, minshare, word, wordshare, worst = {}, nil, nil, nil, 0
  for i = 1, n do
    if wrap[i] then
      share[i] = maxlen[i] / total
      if not minshare or share[i] < minshare then minshare = share[i] end
      for _, r in ipairs(rows) do   -- a wrapped column must be wider than its longest word
        for w in pandoc.utils.stringify(r.cells[i].contents):gmatch("%S+") do
          local ratio = (utf8.len(w) or #w) / share[i]
          if ratio > worst then worst, word, wordshare = ratio, w, share[i] end
        end
      end
    end
  end
  return wrap, share, minshare, word, wordshare, worst
end

-- The complete tabular (wrappable columns P{share}), or its fixed columns alone.
local function tabular(tbl, wrap, share, fixed_only)
  local rows, n = rows_of(tbl), #tbl.colspecs
  local cols = {}
  for i = 1, n do
    if not (fixed_only and wrap[i]) then
      table.insert(cols, {i = i, spec = wrap[i] and string.format("P{%.3f}", share[i]) or "l"})
    end
  end
  if #cols == 0 then return "" end
  local spec = {}
  for _, c in ipairs(cols) do table.insert(spec, c.spec) end
  local out = {"\\begin{tabular}{@{}" .. table.concat(spec) .. "@{}}"}
  if not fixed_only then table.insert(out, "\\toprule") end
  for k, r in ipairs(rows) do
    local cells = {}
    for _, c in ipairs(cols) do table.insert(cells, latex_of(r.cells[c.i].contents)) end
    table.insert(out, table.concat(cells, " & ") .. " \\\\")
    if not fixed_only and r.head and rows[k + 1] and not rows[k + 1].head then
      table.insert(out, "\\midrule")
    end
  end
  if not fixed_only then table.insert(out, "\\bottomrule") end
  table.insert(out, "\\end{tabular}")
  return table.concat(out, "\n")
end

local function has_caption(tbl)
  return tbl.caption and tbl.caption.long and #tbl.caption.long > 0
end

local ntab, nfig = 0, 0

-- Figures omitted from a what-if rendering ($IEEE_DROP_FIGURES, identifiers separated by "|").
local drop_fig = {}
for id in (os.getenv("IEEE_DROP_FIGURES") or ""):gmatch("[^|]+") do drop_fig[id] = true end

function Figure(fig)
  if drop_fig[fig.identifier] then return {} end
  local img
  fig.content:walk({Image = function(el) img = img or el end})
  if not img then return nil end
  nfig = nfig + 1
  local label = fig.identifier ~= "" and fig.identifier or ("ieeefig-" .. nfig)
  table.insert(floats, {label, "figure", img.src, plain(fig.caption.long)})
  return pandoc.RawBlock("latex", "\\IEEEautofigure{" .. label .. "}{" .. img.src .. "}{"
                         .. latex_of(fig.caption.long) .. "}")
end

function Blocks(blocks)
  local out = pandoc.List()
  local i = 1
  while i <= #blocks do
    local b = blocks[i]
    if b.t == "Table" then
      local group = {b}
      if has_caption(b) then
        while blocks[i + 1] and blocks[i + 1].t == "Table" and not has_caption(blocks[i + 1]) do
          i = i + 1
          table.insert(group, blocks[i])
        end
      end
      ntab = ntab + 1
      local label = "ieeetab-" .. ntab
      local parts, minshare = {"\\ieeetableparts{" .. #group .. "}"}, nil
      local word, wordshare, worst = nil, 0, 0
      for k, t in ipairs(group) do
        local wrap, share, m, w, ws, r = roles(t)
        if m and (not minshare or m < minshare) then minshare = m end
        if w and r > worst then word, wordshare, worst = w, ws, r end
        table.insert(parts, "\\ieeedefpart{" .. k .. "}{" .. tabular(t, wrap, share, false) .. "}{"
                     .. tabular(t, wrap, share, true) .. "}")
      end
      local caption = has_caption(b) and latex_of(b.caption.long) or ""
      table.insert(floats, {label, "table", #group .. " part(s)", has_caption(b) and plain(b.caption.long) or "(uncaptioned)"})
      table.insert(parts, "\\IEEEautotable{" .. label .. "}{" .. caption .. "}{"
                   .. string.format("%.3f", minshare or 0) .. "}{"
                   .. (word and latex_of({pandoc.Plain({pandoc.Str(word)})}) or "") .. "}{"
                   .. string.format("%.3f", wordshare) .. "}")
      out:insert(pandoc.RawBlock("latex", table.concat(parts, "\n")))
    else
      out:insert(b)
    end
    i = i + 1
  end
  return out
end

-- Level-1 sections omitted from a what-if rendering ($IEEE_DROP_SECTIONS, titles separated by "|";
-- used by tools/ieee_layout_report.py to measure the effect of moving material out of the paper).
local drop = {}
for title in (os.getenv("IEEE_DROP_SECTIONS") or ""):gmatch("[^|]+") do drop[title] = true end

function Pandoc(doc)
  local out = pandoc.List()
  local i = 1
  while i <= #doc.blocks do
    local b = doc.blocks[i]
    if b.t == "Header" and b.level == 1 and drop[pandoc.utils.stringify(b.content)] then
      i = i + 1
      while i <= #doc.blocks and not (doc.blocks[i].t == "Header" and doc.blocks[i].level == 1) do i = i + 1 end
    elseif b.t == "Header" and b.level == 1 and pandoc.utils.stringify(b.content) == "Abstract" then
      local abstract, keywords = pandoc.List(), nil
      i = i + 1
      while i <= #doc.blocks and not (doc.blocks[i].t == "Header" and doc.blocks[i].level == 1) do
        local p = doc.blocks[i]
        if p.t == "Para" and p.content[1] and p.content[1].t == "Strong"
            and pandoc.utils.stringify(p.content[1]) == "Index Terms" then
          local rest = pandoc.List()
          for k = 2, #p.content do rest:insert(p.content[k]) end
          while rest[1] and (rest[1].t == "Space" or (rest[1].t == "Str" and rest[1].text == ":")) do
            rest:remove(1)
          end
          keywords = latex_of({pandoc.Plain(rest)})
        else
          abstract:insert(p)
        end
        i = i + 1
      end
      local s = "\\begin{abstract}\n" .. pandoc.write(pandoc.Pandoc(abstract), "latex") .. "\n\\end{abstract}"
      if keywords then s = s .. "\n\\begin{IEEEkeywords}\n" .. keywords .. "\n\\end{IEEEkeywords}" end
      out:insert(pandoc.RawBlock("latex", s))
    else
      out:insert(b)
      i = i + 1
    end
  end
  doc.blocks = out
  local path = os.getenv("IEEE_FLOATS_TSV")
  if path then
    local f = assert(io.open(path, "w"))
    f:write("label\tkind\tsource\tcaption\n")
    for _, r in ipairs(floats) do f:write(table.concat(r, "\t") .. "\n") end
    f:close()
  end
  return doc
end
