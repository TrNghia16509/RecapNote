import React, { useState } from "react";
import { ReactMic } from "react-mic";

const MyMic = ({ onStop }) => {
  const [record, setRecord] = useState(false);

  const startRecording = () => setRecord(true);
  const stopRecording = () => setRecord(false);

  return (
    <div style={{ textAlign: "center" }}>
      <ReactMic
        record={record}
        className="sound-wave"
        onStop={onStop}
        strokeColor="#000000"
        backgroundColor="#FF4081"
        mimeType="audio/wav"
      />
      <br />
      <button onClick={startRecording} disabled={record}>🎙 Bắt đầu</button>
      <button onClick={stopRecording} disabled={!record}>⏹ Dừng</button>
    </div>
  );
};

export default MyMic;
