import React, { useState } from "react";
import { ReactMic } from "react-mic";

const MyMic = ({ onStop }) => {
  const [record, setRecord] = useState(false);

  const startRecording = () => setRecord(true);
  const stopRecording = () => setRecord(false);

  const handleStop = (recordedBlob) => {
    const reader = new FileReader();
    reader.readAsDataURL(recordedBlob.blob);
    reader.onloadend = () => {
      const base64data = reader.result;
      // Gửi về Streamlit
      window.parent.postMessage({ type: "streamlit:setComponentValue", value: base64data }, "*");
    };
    if (onStop) onStop(recordedBlob);
  };

  return (
    <div style={{ textAlign: "center" }}>
      <ReactMic
        record={record}
        className="sound-wave"
        onStop={handleStop}
        strokeColor="#000000"
        backgroundColor="#FF4081"
      />
      <div style={{ marginTop: "10px" }}>
        <button onClick={startRecording}>🎙 Bắt đầu</button>
        <button onClick={stopRecording}>⏹ Dừng</button>
      </div>
    </div>
  );
};

export default MyMic;
