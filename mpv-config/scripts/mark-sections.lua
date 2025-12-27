local sections = {}
local current_start = nil

function clear_sections()
    sections = {}
    current_start = nil
    mp.osd_message("Sections cleared", 1)
end

mp.register_event("file-loaded", clear_sections)

function mark_start()
    local time = mp.get_property_number("time-pos")
    current_start = time
    mp.osd_message(string.format("Start marked: %.1f", time), 2)
end

function mark_end()
    if current_start == nil then
        mp.osd_message("No start marked!", 2)
        return
    end
    local time = mp.get_property_number("time-pos")
    if time <= current_start then
        mp.osd_message("End must be after start!", 2)
        return
    end
    table.insert(sections, {start = current_start, finish = time})
    mp.osd_message(string.format("Section marked: %.1f-%.1f", current_start, time), 2)
    current_start = nil
end

function write_sections()
    local filename = mp.get_property("path")
    local output = filename .. ".sections"
    local file = io.open(output, "w")
    for _, section in ipairs(sections) do
        file:write(string.format("%.1f-%.1f\n", section.start, section.finish))
    end
    file:close()
    mp.osd_message(string.format("Wrote %d sections to %s", #sections, output), 3)
end

function run_remove_sections()
    local filename = mp.get_property("path")
    local sections_file = filename .. ".sections"
    
    -- First write the sections
    local file = io.open(sections_file, "w")
    for _, section in ipairs(sections) do
        file:write(string.format("%.1f-%.1f\n", section.start, section.finish))
    end
    file:close()
    
    -- Run remove-sections and capture output
    local dir = filename:match("(.*/)")
    local cmd = string.format("cd '%s' && remove-sections '%s' -f '%s' > /tmp/mpv-remove.log 2>&1", dir, filename, sections_file)
    mp.osd_message("Running remove-sections...", 3)
    os.execute(cmd)
    mp.osd_message("Done - log output in /tmp/mpv-remove.log", 3)
end

mp.add_key_binding("[", "mark-start", mark_start)
mp.add_key_binding("]", "mark-end", mark_end)
mp.add_key_binding("w", "write-sections", write_sections)
mp.add_key_binding("r", "run-remove-sections", run_remove_sections)

