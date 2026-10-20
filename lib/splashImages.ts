// iOS startup pictures (apple-touch-startup-image) for the start screen
// (lib/caSplash.ts): one per screen size and orientation, white with the CA sign
// 200 CSS px in the middle — the same place and size as the start screen's first
// frame. Sizes: lib/splash-devices.json; pictures: scripts/splash_images.py.
// The 44 <link>s are written by a small <head> script (iOS reads them when the
// book is added to the home screen): as static tags they cost ~11 KB in every
// page and again in every page's payload (the offline copy of the book).
import devices from "./splash-devices.json";
import { BASE_PATH } from "./basePath";

const list = JSON.stringify(devices.map(({ w, h, dpr }) => [w, h, dpr]));

export const SPLASH_LINKS_SCRIPT = `(function(){try{var h=document.head;${list}.forEach(function(x){["portrait","landscape"].forEach(function(o){var p=o==="portrait",l=document.createElement("link");l.rel="apple-touch-startup-image";l.href=${JSON.stringify(
  `${BASE_PATH}/splash/ios-`,
)}+(p?x[0]*x[2]+"x"+x[1]*x[2]:x[1]*x[2]+"x"+x[0]*x[2])+".png";l.media="(device-width: "+x[0]+"px) and (device-height: "+x[1]+"px) and (-webkit-device-pixel-ratio: "+x[2]+") and (orientation: "+o+")";h.appendChild(l)})})}catch(e){}})();`;
