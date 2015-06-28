gl.setup(1920, 1080)

node.alias "multiscreen"

local json = require 'json'

local screen, video

local function setup_screen(screen_id, config)
    screen = config.screens[screen_id+1]
    local diagonal_pixels = math.sqrt(math.pow(screen.width, 2) + math.pow(screen.height, 2))
    local cm_per_pixel = (screen.inches * 2.54) / diagonal_pixels

    gl.setup(screen.width, screen.height)
    screen.x = screen.x / cm_per_pixel
    screen.y = screen.y / cm_per_pixel
    print(('initialized %d" screen %d (%dx%d)'):format(screen.inches, screen_id, screen.width, screen.height))

    video = config.video
    video.x = video.x / cm_per_pixel
    video.y = video.y / cm_per_pixel
    video.width = video.width / cm_per_pixel
    video.height = video.height / cm_per_pixel
end

local player = (function()
    local res, next_res, master
    node.event("connect", function(new_master)
        if master then node.client_disconnect(master) end
        master = new_master
        print("master connected")
    end)

    node.event("disconnect", function(client)
        assert(client == master)
        print("master disconnected")
        master = nil
    end)

    -- {"cmd": "load", "filename": "optical.mp4"}
    -- {"cmd": "start"}
    -- {"cmd": "config", "config": {...}, "screen_id": 1234}
    node.event("input", function(pkt, client)
        print(pkt)
        assert(client == master)
        pkt = json.decode(pkt)
        pp(pkt)
        if pkt.cmd == "load" then
            if next_res then next_res:dispose() end
            next_res = resource.load_video(pkt.filename, false, false, true)
        elseif pkt.cmd == "start" then
            if res then res:dispose() end
            res = next_res
            next_res = nil
            res:start()
        elseif pkt.cmd == "config" then
            setup_screen(pkt.screen_id, pkt.config)
        end
    end)

    local function send_state(state)
        if master then
            node.client_write(master, state)
        end
    end

    local function tick()
        if next_res then
            send_state(next_res:state())
        elseif res then
            send_state(res:state())
        else
            send_state("none")
        end
    end

    local function draw(x1, y1, x2, y2)
        if res then
            res:draw(x1, y1, x2, y2)
        end
    end

    return {
        tick = tick;
        draw = draw;
    }
end)()

function node.render()
    gl.clear(0,0,0,1)
    player.tick()
    if screen and video then
        gl.rotate(-screen.rotation, 0, 0, 1)
        gl.translate(-screen.x, -screen.y)
        player.draw(video.x, video.y, video.x+video.width, video.y+video.height)
    end
end
