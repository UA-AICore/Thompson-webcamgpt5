
import {io} from "https://cdn.skypack.dev/socket.io-client";
import {processImage} from "./webcam.js";


let curData = null;
const socket = io();
socket.on('image_created', (data) => {
    if (curData !== null && curData.base64_image === data.base64_image) {
        console.log("Image already processed");
        return;
    } 
    curData = data;
    processImage(data.base64_image);
});