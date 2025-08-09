import React from "react";
import ReactDOM from "react-dom";
import MyMic from "./MyMic";
import { Streamlit, withStreamlitConnection } from "streamlit-component-lib";

const Component = (props) => {
  const onStop = (recordedBlob) => {
    fetch(recordedBlob.blobURL)
      .then(res => res.blob())
      .then(blob => {
        blob.arrayBuffer().then(buffer => {
          const byteArray = new Uint8Array(buffer);
          Streamlit.setComponentValue(Array.from(byteArray));
        });
      });
  };
  return <MyMic onStop={onStop} />;
};

const Wrapped = withStreamlitConnection(Component);
ReactDOM.render(<Wrapped />, document.getElementById("root"));
