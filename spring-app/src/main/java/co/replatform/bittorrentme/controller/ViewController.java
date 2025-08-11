package co.replatform.bittorrentme.controller;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class ViewController {
    @GetMapping({"/", "/index"})
    public String index() {
        // Serve static index.html from resources/static
        return "forward:/index.html";
    }
}


