import fs from "node:fs";
import path from "node:path";
import {execFileSync} from "node:child_process";
import puppeteer from "puppeteer";

const ROOT=process.cwd();
const BUILD=path.join(ROOT,"build-proof");
const FRAMES=path.join(BUILD,"frames");
const width=720,height=1280,fps=24,seconds=10;

fs.rmSync(BUILD,{recursive:true,force:true});
fs.mkdirSync(FRAMES,{recursive:true});

const browser=await puppeteer.launch({
  headless:true,
  executablePath:process.env.CHROME_PATH||"/usr/bin/chromium",
  args:["--no-sandbox","--disable-setuid-sandbox","--disable-gpu"]
});

try{
  const page=await browser.newPage();
  await page.setViewport({width,height,deviceScaleFactor:1});
  await page.goto("file://"+path.join(ROOT,"animation.html"),{waitUntil:"load"});
  await page.waitForFunction(()=>window.__renderReady===true);

  for(let i=0;i<fps*seconds;i++){
    const t=i/fps;
    await page.evaluate(time=>window.__renderFrame(time),t);
    await page.screenshot({
      path:path.join(FRAMES,"frame-"+String(i).padStart(5,"0")+".png"),
      type:"png"
    });
  }
}finally{
  await browser.close();
}

const output=path.join(BUILD,"stickman-proof.mp4");
execFileSync("ffmpeg",[
  "-y","-hide_banner","-loglevel","error",
  "-framerate",String(fps),
  "-i",path.join(FRAMES,"frame-%05d.png"),
  "-c:v","libx264","-preset","medium","-crf","18",
  "-pix_fmt","yuv420p","-movflags","+faststart",output
],{stdio:"inherit"});

console.log(output);
