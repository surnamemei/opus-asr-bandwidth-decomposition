-- Pandoc Lua filter (LaTeX output only; presentation only).
-- Emits every table as a float (caption above, booktabs rules) instead of a page-breaking
-- longtable. A captioned table followed immediately by uncaptioned tables is set as one
-- float. Column widths follow the longest cell; a table too wide for its natural width is
-- set with tabularx. Confidence intervals "[a, b]" are kept on one line.
if not FORMAT:match("latex") then return {} end

local function latex_of(blocks)
  local s = pandoc.write(pandoc.Pandoc(blocks), "latex")
  s = s:gsub("\n+$", ""):gsub("\n", " ")
  -- keep "[lo, hi]" together (pandoc writes brackets as {[} ... {]})
  s = s:gsub("({%[}[^{]-),%s+([^{]-{%]})", "%1,~%2")
  return s
end

local function cell_text(cell) return pandoc.utils.stringify(cell.contents) end

local function rows_of(tbl)
  local rows = {}
  for _, r in ipairs(tbl.head.rows) do table.insert(rows, {head = true, cells = r.cells}) end
  for _, body in ipairs(tbl.bodies) do
    for _, r in ipairs(body.body) do table.insert(rows, {head = false, cells = r.cells}) end
  end
  return rows
end

local SHORT = 12  -- columns up to this many characters are not wrapped

local function tabular(tbl)
  local rows = rows_of(tbl)
  local n = #tbl.colspecs
  local maxlen = {}
  for i = 1, n do maxlen[i] = 1 end
  for _, r in ipairs(rows) do
    for i, c in ipairs(r.cells) do
      local len = utf8.len(cell_text(c)) or #cell_text(c)
      if len > maxlen[i] then maxlen[i] = len end
    end
  end
  local total = 0
  for i = 1, n do total = total + maxlen[i] end
  -- a column is "fixed" (never wrapped) if it is short or holds only numbers/intervals
  local fixed = {}
  for i = 1, n do fixed[i] = maxlen[i] <= SHORT end
  for i = 1, n do
    local allnum = true
    for _, r in ipairs(rows) do
      if not r.head then
        local t = cell_text(r.cells[i])
        if not (t:match("^[%s%d%.,%[%]%+%-−—]*$")) then allnum = false end
      end
    end
    if allnum then fixed[i] = true end
  end
  local fixedlen, nflex = 0, 0
  for i = 1, n do
    if fixed[i] then fixedlen = fixedlen + maxlen[i] else nflex = nflex + 1 end
  end
  local env, spec, size = "tabular", string.rep("l", n), "\\small"
  if total + 3 * n > 100 then
    env = "tabularx"
    local need = fixedlen + 2 * n + 25 * nflex
    if nflex > 0 and need <= 100 then
      spec = ""
    elseif nflex > 0 and need <= 118 then
      spec, size = "", "\\footnotesize"
    else
      -- does not fit unwrapped: every long column shares the width by length
      for i = 1, n do fixed[i] = maxlen[i] <= SHORT end
      fixedlen, nflex = 0, 0
      for i = 1, n do
        if fixed[i] then fixedlen = fixedlen + maxlen[i] else nflex = nflex + 1 end
      end
      spec = ""
    end
    local flextotal = total - fixedlen
    local parts = {}
    for i = 1, n do
      if fixed[i] then
        table.insert(parts, "l")
      else
        table.insert(parts, string.format(">{\\hsize=%.3f\\hsize}Y", maxlen[i] * nflex / flextotal))
      end
    end
    spec = table.concat(parts)
  end
  local out = {size}
  if n >= 7 then table.insert(out, "\\setlength{\\tabcolsep}{4pt}") end
  if env == "tabularx" then
    table.insert(out, "\\begin{tabularx}{\\linewidth}{@{}" .. spec .. "@{}}")
  else
    table.insert(out, "\\begin{tabular}{@{}" .. spec .. "@{}}")
  end
  table.insert(out, "\\toprule")
  for k, r in ipairs(rows) do
    local cells = {}
    for _, c in ipairs(r.cells) do table.insert(cells, latex_of(c.contents)) end
    table.insert(out, table.concat(cells, " & ") .. " \\\\")
    if r.head and rows[k + 1] and not rows[k + 1].head then table.insert(out, "\\midrule") end
  end
  table.insert(out, "\\bottomrule")
  table.insert(out, env == "tabularx" and "\\end{tabularx}" or "\\end{tabular}")
  return table.concat(out, "\n")
end

local function has_caption(tbl)
  return tbl.caption and tbl.caption.long and #tbl.caption.long > 0
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
      local s = {}
      table.insert(s, has_caption(b) and "\\begin{table}" or "\\begin{table}[H]")
      table.insert(s, "\\centering")
      if has_caption(b) then
        local cap = latex_of(b.caption.long)
        local label = (b.identifier and b.identifier ~= "") and ("\\label{" .. b.identifier .. "}") or ""
        table.insert(s, "\\caption{" .. cap .. "}" .. label)
      end
      for k, t in ipairs(group) do
        if k > 1 then table.insert(s, "\\par\\medskip") end
        table.insert(s, tabular(t))
      end
      table.insert(s, "\\end{table}")
      out:insert(pandoc.RawBlock("latex", table.concat(s, "\n")))
    else
      out:insert(b)
    end
    i = i + 1
  end
  return out
end
