import { useEffect, useRef, useState } from "react";
import "./App.css";

const API_BASE_URL = "https://brainmagictechnova--product-catalog-backend-fastapi-app.modal.run";
const getProductImageUrl = (imageName) => {
  if (!imageName) {
    return null;
  }

  const cleanImageName = String(imageName).trim();

  if (!cleanImageName) {
    return null;
  }

  return `${API_BASE_URL}/product-images/${encodeURIComponent(
    cleanImageName
  )}`;
};

function App() {
  // =========================================================
  // CHAT WINDOW
  // =========================================================

  const [isChatOpen, setIsChatOpen] = useState(true);

  // =========================================================
  // MESSAGE INPUT
  // =========================================================

  const [message, setMessage] = useState("");

  // =========================================================
  // CHAT MESSAGES
  // =========================================================

  const [messages, setMessages] = useState([]);

  // =========================================================
  // LOADING
  // =========================================================

  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isVoiceProcessing, setIsVoiceProcessing] = useState(false);

  // =========================================================
  // MESSAGE AREA REF
  // =========================================================

  const messagesEndRef = useRef(null);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const speechSynthesisRef = useRef(null);
  const currentUtteranceRef = useRef(null);

  const [speakingMessageId, setSpeakingMessageId] = useState(null);
  const [playedMessageIds, setPlayedMessageIds] = useState(new Set());

  // =========================================================
  // AUTO SCROLL
  // =========================================================

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, isLoading]);

  useEffect(() => {
    if ("speechSynthesis" in window) {
      speechSynthesisRef.current = window.speechSynthesis;
    }

    return () => {
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }

      currentUtteranceRef.current = null;
    };
  }, []);

  // =========================================================
  // START VOICE RECORDING
  // =========================================================

  const startRecording = async () => {
    stopSpeech();
    if (isLoading || isRecording) {
      return;
    }

    try {
      const stream =
        await navigator.mediaDevices.getUserMedia({
          audio: true,
        });

      audioChunksRef.current = [];

      const mediaRecorder =
        new MediaRecorder(stream);

      mediaRecorderRef.current =
        mediaRecorder;

      mediaRecorder.ondataavailable = (
        event
      ) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(
            event.data
          );
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob =
          new Blob(
            audioChunksRef.current,
            {
              type:
                mediaRecorder.mimeType ||
                "audio/webm",
            }
          );

        // Stop microphone
        stream
          .getTracks()
          .forEach((track) => {
            track.stop();
          });

        await sendVoiceToBackend(
          audioBlob
        );
      };

      mediaRecorder.start();

      setIsRecording(true);

    } catch (error) {

      console.error(
        "Microphone access failed:",
        error
      );

      alert(
        "Microphone permission is required."
      );
    }
  };

  // =========================================================
  // STOP VOICE RECORDING
  // =========================================================

  const stopRecording = () => {
    if (
      !mediaRecorderRef.current ||
      !isRecording
    ) {
      return;
    }

    mediaRecorderRef.current.stop();

    setIsRecording(false);
  };

  // =========================================================
  // SEND VOICE TO BACKEND
  // =========================================================

  const sendVoiceToBackend = async (
    audioBlob
  ) => {

    setIsVoiceProcessing(true);

    try {

      const formData =
        new FormData();

      formData.append(
        "audio",
        audioBlob,
        "recording.webm"
      );

      const response =
        await fetch(
          `${API_BASE_URL}/api/voice`,
          {
            method: "POST",
            body: formData,
          }
        );

      const data =
        await response.json();

      if (
        !response.ok ||
        !data.success
      ) {
        throw new Error(
          data.error ||
          data.message ||
          "Voice transcription failed."
        );
      }

      const voiceData =
        data.data || {};

      const transcribedText =
        voiceData.text || "";

      const detectedLanguage =
        voiceData.language || "";

      console.log(
        "Voice text:",
        transcribedText
      );

      console.log(
        "Detected language:",
        detectedLanguage
      );

      // Put transcription into textbox
      setMessage(
        transcribedText
      );

    } catch (error) {

      console.error(
        "Voice request failed:",
        error
      );

      alert(
        "Could not convert your voice to text."
      );

    } finally {

      setIsVoiceProcessing(false);
    }
  };

  // =========================================================
  // SEND MESSAGE
  // =========================================================
  
  const stopSpeech = () => {
    if (speechSynthesisRef.current) {
      speechSynthesisRef.current.cancel();
    }

    currentUtteranceRef.current = null;
    setSpeakingMessageId(null);
  };
  
  const speakMessage = (chatMessage) => {
    if (!chatMessage?.text) return;

    if (!("speechSynthesis" in window)) {
      console.warn("Browser does not support Speech Synthesis.");
      return;
    }

    const synthesis = speechSynthesisRef.current || window.speechSynthesis;

    // If the same message is currently speaking, stop it
    if (speakingMessageId === chatMessage.id) {
      stopSpeech();
      return;
    }

    // Stop any previously playing message
    synthesis.cancel();

    const text = String(chatMessage.text).trim();

    if (!text) return;

    const utterance = new SpeechSynthesisUtterance(text);

    utterance.onstart = () => {
      setSpeakingMessageId(chatMessage.id);
    };

    utterance.onend = () => {
      if (currentUtteranceRef.current === utterance) {
        currentUtteranceRef.current = null;
        setSpeakingMessageId(null);

        setPlayedMessageIds((previousIds) => {
          const updatedIds = new Set(previousIds);
          updatedIds.add(chatMessage.id);
          return updatedIds;
        });
      }
    };

    utterance.onerror = () => {
      if (currentUtteranceRef.current === utterance) {
        currentUtteranceRef.current = null;
        setSpeakingMessageId(null);
      }
    };

    currentUtteranceRef.current = utterance;

    setSpeakingMessageId(chatMessage.id);

    synthesis.speak(utterance);
  };

  const sendMessage = async (selectedMessage = null) => {
    // -------------------------------------------------------
    // DETERMINE MESSAGE
    // -------------------------------------------------------

    const textToSend =
      selectedMessage !== null
        ? String(selectedMessage).trim()
        : message.trim();

    // -------------------------------------------------------
    // EMPTY MESSAGE
    // -------------------------------------------------------

    if (!textToSend) {
      return;
    }

    // -------------------------------------------------------
    // PREVENT DOUBLE REQUEST
    // -------------------------------------------------------

    if (isLoading) {
      return;
    }

    stopSpeech();

    // -------------------------------------------------------
    // ADD USER MESSAGE
    // -------------------------------------------------------

    setMessages((previousMessages) => [
      ...previousMessages,
      {
        id: Date.now() + Math.random(),
        sender: "user",
        text: textToSend,
      },
    ]);

    // -------------------------------------------------------
    // CLEAR INPUT
    // -------------------------------------------------------

    setMessage("");

    // -------------------------------------------------------
    // START LOADING
    // -------------------------------------------------------

    setIsLoading(true);

    try {
      // =====================================================
      // CALL BACKEND
      // =====================================================

      const response = await fetch(
        `${API_BASE_URL}/api/chat`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify({
            message: textToSend,
          }),
        }
      );

      // =====================================================
      // READ JSON
      // =====================================================

      const data = await response.json();

      // =====================================================
      // BACKEND ERROR
      // =====================================================

      if (!response.ok || !data.success) {
        throw new Error(
          data.error ||
            data.message ||
            "Something went wrong."
        );
      }

      // =====================================================
      // BACKEND DATA
      // =====================================================

      const backendData = data.data || {};

      const result = backendData.result || {};

      // =====================================================
      // AI MESSAGE
      // =====================================================

      let aiText = "";

      if (
        result.message !== undefined &&
        result.message !== null &&
        String(result.message).trim() !== ""
      ) {
        aiText = String(result.message);
      } else if (
        result.question !== undefined &&
        result.question !== null &&
        String(result.question).trim() !== ""
      ) {
        aiText = String(result.question);
      } else {
        aiText =
          "I received your request, but I could not generate a response.";
      }

      // =====================================================
      // DYNAMIC OPTIONS
      // =====================================================

      let options = [];

      if (Array.isArray(result.options)) {
        options = result.options;
      } else if (Array.isArray(backendData.options)) {
        options = backendData.options;
      }

      // -------------------------------------------------------
      // REMOVE EMPTY OPTIONS
      // -------------------------------------------------------

      options = options.filter(
        (option) =>
          option !== null &&
          option !== undefined &&
          String(option).trim() !== ""
      );

      // =====================================================
      // ACTION
      // =====================================================

      const action =
        result.action ||
        backendData.action ||
        null;

      // =====================================================
      // FIELD
      // =====================================================

      const field =
        result.field ||
        backendData.field ||
        null;

      const presentationFormat =
        result.presentation_format ||
        backendData.presentation_format ||
        null;

      // =====================================================
      // RAW RECORDS
      // =====================================================

      const records = Array.isArray(result.records)
        ? result.records
        : Array.isArray(backendData.records)
        ? backendData.records
        : [];

      // =====================================================
      // FRONTEND MAPPED RECORDS
      // =====================================================
      //
      // Backend FrontendMapper should provide:
      //
      // frontend_records
      //
      // Example:
      //
      // {
      //   "Image": "...",
      //   "Part Number": "...",
      //   "Engine": "...",
      //   "OEM": "BMW",
      //   "Model": "X5",
      //   "Year": "2021"
      // }
      //
      // =====================================================

      let frontendRecords = [];

      if (Array.isArray(result.frontend_records)) {
        frontendRecords = result.frontend_records;
      } else if (
        Array.isArray(backendData.frontend_records)
      ) {
        frontendRecords = backendData.frontend_records;
      }

      // =====================================================
      // SUPPORT SINGLE FRONTEND RECORD
      // =====================================================

      if (
        frontendRecords.length === 0 &&
        result.frontend_record &&
        typeof result.frontend_record === "object"
      ) {
        frontendRecords = [
          result.frontend_record,
        ];
      }

      if (
        frontendRecords.length === 0 &&
        backendData.frontend_record &&
        typeof backendData.frontend_record === "object"
      ) {
        frontendRecords = [
          backendData.frontend_record,
        ];
      }

      // =====================================================
      // CLEAN FRONTEND RECORDS
      // =====================================================

      frontendRecords = frontendRecords.filter(
        (record) =>
          record &&
          typeof record === "object" &&
          !Array.isArray(record)
      );

      // =====================================================
      // DEBUG
      // =====================================================

      console.log(
        "Frontend mapped records:",
        frontendRecords
      );

      // =====================================================
      // ADD AI MESSAGE
      // =====================================================

      const aiMessage = {
        id: Date.now() + Math.random(),

        sender: "ai",

        text: aiText,

        // Dynamic AI options
        options: options,

        // Conversation information
        action: action,

        field: field,

        presentationFormat: presentationFormat,

        // Raw records
        records: records,

        // Frontend mapped records
        frontendRecords: frontendRecords,
      };

      setMessages((previousMessages) => [
        ...previousMessages,
        aiMessage,
      ]);

      // Automatically speak the AI response
      speakMessage(aiMessage);
    } catch (error) {
      // =====================================================
      // ERROR
      // =====================================================

      console.error(
        "Backend request failed:",
        error
      );

      setMessages((previousMessages) => [
        ...previousMessages,

        {
          id: Date.now() + Math.random(),

          sender: "ai",

          text:
            "Sorry, I couldn't connect to the AI Product Catalog.",

          options: [],

          frontendRecords: [],
        },
      ]);
    } finally {
      // =====================================================
      // STOP LOADING
      // =====================================================

      setIsLoading(false);
    }
  };

  // =========================================================
  // OPTION CLICK
  // =========================================================

  const handleOptionClick = (option) => {
    if (isLoading) {
      return;
    }

    const selectedOption = String(option).trim();

    if (!selectedOption) {
      return;
    }

    sendMessage(selectedOption);
  };

  // =========================================================
  // ENTER KEY
  // =========================================================

  const handleKeyDown = (event) => {
    if (event.key === "Enter") {
      event.preventDefault();

      if (!isLoading) {
        sendMessage();
      }
    }
  };

  // =========================================================
  // RESET CHAT
  // =========================================================

  const resetChat = async () => {
    if (isLoading) {
      return;
    }

    try {
      setIsLoading(true);

      // -----------------------------------------------------
      // RESET BACKEND
      // -----------------------------------------------------

      const response = await fetch(
        `${API_BASE_URL}/api/reset`,
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(
          data.error ||
            "Failed to reset conversation."
        );
      }

      // -----------------------------------------------------
      // RESET FRONTEND
      // -----------------------------------------------------

      setMessages([]);

      setMessage("");
    } catch (error) {
      console.error(
        "Reset failed:",
        error
      );

      setMessages((previousMessages) => [
        ...previousMessages,

        {
          id: Date.now() + Math.random(),

          sender: "ai",

          text:
            "I couldn't reset the conversation.",

          options: [],

          frontendRecords: [],
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // =========================================================
  // CLOSE CHAT
  // =========================================================

  const closeChat = () => {
    setIsChatOpen(false);
  };

  // =========================================================
  // OPEN CHAT
  // =========================================================

  const openChat = () => {
    setIsChatOpen(true);
  };

  // =========================================================
  // IMAGE HELPER
  // =========================================================

  const getImageSource = (imageValue) => {
    if (!imageValue) {
      return null;
    }

    const imageString = String(imageValue).trim();

    if (!imageString) {
      return null;
    }

    // -------------------------------------------------------
    // Already a complete URL
    // -------------------------------------------------------

    if (
      imageString.startsWith("http://") ||
      imageString.startsWith("https://") ||
      imageString.startsWith("data:image/")
    ) {
      return imageString;
    }

    // -------------------------------------------------------
    // Already backend product-image path
    // Example:
    // /product-images/5pk.jpg
    // -------------------------------------------------------

    if (
      imageString.startsWith("/product-images/")
    ) {
      return `${API_BASE_URL}${imageString}`;
    }

    // -------------------------------------------------------
    // Image filename from database
    // Example:
    // 5pk.jpg
    //
    // Convert to:
    // http://127.0.0.1:8000/product-images/5pk.jpg
    // -------------------------------------------------------

    const cleanFileName =
      imageString.startsWith("/")
        ? imageString.substring(1)
        : imageString;

    return `${API_BASE_URL}/product-images/${encodeURIComponent(
      cleanFileName
    )}`;
  };
    
  // =========================================================
  // PRODUCT DETAILS CARD
  // =========================================================

  const ProductDetailsCard = ({
    record,
    index,
  }) => {
    if (!record || typeof record !== "object") {
      return null;
    }

    // -------------------------------------------------------
    // IMAGE
    // -------------------------------------------------------

    const imageValue =
      record["Image"] ||
      record["image"] ||
      null;

    const imageSource =
      getImageSource(imageValue);

    // -------------------------------------------------------
    // FRONTEND MAPPED FIELDS
    // -------------------------------------------------------
    //
    // IMPORTANT:
    //
    // These are the names produced by FrontendMapper.
    //
    // Frontend does NOT convert:
    //
    // fenner -> Part Number
    //
    // itself.
    //
    // Backend FrontendMapper already does that.
    //
    // -------------------------------------------------------

    const displayFields = [
      "Part Number",
      "Engine",
      "OEM",
      "Model",
      "Year",
      "ProductType",
      "Competitor PartNo",
      "Category",
      "GatesPartNumber",
      "Status",
      "Routing Guide",
    ];

    // -------------------------------------------------------
    // ONLY SHOW FIELDS WHICH HAVE VALUES
    // -------------------------------------------------------

    const fields = displayFields.filter(
      (fieldName) =>
        record[fieldName] !== null &&
        record[fieldName] !== undefined &&
        String(record[fieldName]).trim() !== ""
    );

    return (
      <div
        className="product-details-card"
        key={index}
      >

        {/* =================================================
            CARD HEADER
        ================================================= */}

        <div className="product-card-header">

          <div className="product-card-icon">
            📦
          </div>

          <div>
            <div className="product-card-title">
              Product Details
            </div>

            <div className="product-card-subtitle">
              Matching Catalog Product
            </div>
          </div>

        </div>

        {/* =================================================
            PRODUCT IMAGE
        ================================================= */}

        {imageSource && (
          <div className="product-image-container">

            <img
              src={imageSource}
              alt="Product"
              className="product-image"
              onError={(event) => {
                event.currentTarget.style.display =
                  "none";
              }}
            />

          </div>
        )}

        {/* =================================================
            PRODUCT FIELDS
        ================================================= */}

        <div className="product-card-fields">

          {fields.map(
            (fieldName) => (

              <div
                className="product-field-row"
                key={fieldName}
              >

                <div className="product-field-label">
                  {fieldName}
                </div>

                <div className="product-field-value">
                  {String(
                    record[fieldName]
                  )}
                </div>

              </div>

            )
          )}

        </div>

      </div>
    );
  };
    
    // =========================================================
  // PRODUCT DETAILS TABLE
  // =========================================================

  const ProductDetailsTable = ({
    records,
  }) => {

    if (
      !Array.isArray(records) ||
      records.length === 0
    ) {
      return null;
    }

    const displayFields = [
      "Part Number",
      "Engine",
      "OEM",
      "Model",
      "Year",
      "ProductType",
      "Competitor PartNo",
      "Category",
      "GatesPartNumber",
      "Status",
      "Routing Guide",
    ];

    // -------------------------------------------------------
    // Only keep columns which contain at least one value.
    // -------------------------------------------------------

    const fields = displayFields.filter(
      (fieldName) =>
        records.some(
          (record) =>
            record &&
            record[fieldName] !== null &&
            record[fieldName] !== undefined &&
            String(
              record[fieldName]
            ).trim() !== ""
        )
    );

    if (fields.length === 0) {
      return null;
    }

    return (
      <div className="product-table-container">

        <div className="product-table-header">
          <div className="product-table-title">
            Product Details
          </div>

          <div className="product-table-subtitle">
            Matching Catalog Products
          </div>
        </div>

        <div className="product-table-wrapper">

          <table className="product-details-table">

            <thead>
              <tr>
                {fields.map(
                  (fieldName) => (
                    <th key={fieldName}>
                      {fieldName}
                    </th>
                  )
                )}
              </tr>
            </thead>

            <tbody>

              {records.map(
                (record, recordIndex) => (

                  <tr
                    key={recordIndex}
                  >

                    {fields.map(
                      (fieldName) => (

                        <td
                          key={fieldName}
                        >
                          {record[
                            fieldName
                          ] !== null &&
                          record[
                            fieldName
                          ] !== undefined &&
                          String(
                            record[
                              fieldName
                            ]
                          ).trim() !== ""
                            ? String(
                                record[
                                  fieldName
                                ]
                              )
                            : "—"}
                        </td>

                      )
                    )}

                  </tr>

                )
              )}

            </tbody>

          </table>

        </div>

      </div>
    );
  };
  // =========================================================
  // CHAT CLOSED
  // =========================================================

  if (!isChatOpen) {
    return (
      <div className="app-container">

        <button
          className="ai-chat-open-button"
          onClick={openChat}
          type="button"
        >
          AI Chat
        </button>

      </div>
    );
  }

  // =========================================================
  // CHAT UI
  // =========================================================

  return (
    <div className="app-container">

      <div className="chat-window">

        {/* =================================================
            HEADER
        ================================================= */}

        <div className="chat-header">

          <div className="header-left">

            <div className="ai-logo">
              <img
                src="/company-logo.png"
                alt="Company Logo"
              />
            </div>

            <div className="header-text">

              <div className="header-title">
                AI Product Catalog
              </div>

              <div className="header-subtitle">
                Product Assistant
              </div>

            </div>

          </div>

          <div className="header-actions">

            {/* Language */}

            <button
              className="header-button"
              title="Language"
              type="button"
            >
              🌐
            </button>

            {/* Reset */}

            <button
              className="header-button"
              title="Reset conversation"
              onClick={resetChat}
              disabled={isLoading}
              type="button"
            >
              ↻
            </button>

            {/* Close */}

            <button
              className="header-button"
              title="Close"
              onClick={closeChat}
              type="button"
            >
              ×
            </button>

          </div>

        </div>

        {/* =================================================
            MESSAGE AREA
        ================================================= */}

        <div className="chat-messages">

          {/* =================================================
              WELCOME
          ================================================= */}

          {messages.length === 0 &&
            !isLoading && (

              <div className="welcome-container">

                <div className="welcome-icon">
                  🤖
                </div>

                <h2>
                  Welcome!
                </h2>

                <p>
                  Tell me which vehicle or product
                  you are looking for.
                </p>

              </div>

            )}

          {/* =================================================
              CHAT MESSAGES
          ================================================= */}

          {messages.map(
            (chatMessage) => (

              <div
                key={chatMessage.id}
                className={
                  chatMessage.sender === "user"
                    ? "message-row user-row"
                    : "message-row ai-row"
                }
              >
              
                <div className="message-content">

                {/* =========================================
                    MESSAGE BUBBLE
                ========================================= */}
                <div
                  className={
                    chatMessage.sender === "user"
                      ? "message-bubble user-bubble"
                      : "message-bubble ai-bubble"
                  }
                >

                  {/* =========================================
                      MESSAGE TEXT
                  ========================================= */}

                  <div className="message-text">
                    {chatMessage.text}
                  </div>
                  {/* =========================================
                      AI TEXT-TO-SPEECH
                  ========================================= */}
                  {chatMessage.sender === "ai" && (
                    <div className="message-speech-control">

                      <button
                        type="button"
                        className={`speaker-button ${
                          speakingMessageId === chatMessage.id
                            ? "speaking"
                            : ""
                        }`}
                        onClick={() => speakMessage(chatMessage)}
                        title={
                          speakingMessageId === chatMessage.id
                            ? "Stop voice"
                            : playedMessageIds.has(chatMessage.id)
                            ? "Replay voice"
                            : "Play voice"
                        }
                        aria-label={
                          speakingMessageId === chatMessage.id
                            ? "Stop voice response"
                            : playedMessageIds.has(chatMessage.id)
                            ? "Replay voice response"
                            : "Play voice response"
                        }
                      >

                        {speakingMessageId === chatMessage.id
                          ? "🔊"
                          : "🔈"}

                      </button>

                      {/* Replay icon */}
                      {playedMessageIds.has(chatMessage.id) &&
                        speakingMessageId !== chatMessage.id && (
                          <span
                            className="replay-icon"
                            title="Replay voice"
                          >
                            ↻
                          </span>
                        )}

                    </div>
                  )}
                  

                  {/* =========================================
                      AI OPTIONS
                  ========================================= */}

                  {chatMessage.sender === "ai" &&
                    Array.isArray(chatMessage.options) &&
                    chatMessage.options.length > 0 && (

                      <div className="chat-options">

                        {chatMessage.options.map(
                          (option,optionIndex) => (

                            <button
                              key={
                                `${chatMessage.id}-${optionIndex}`
                              }
                              className="chat-option-button"
                              type="button"
                              disabled={isLoading}
                              onClick={() =>
                                handleOptionClick(
                                  option
                                )
                              }
                            >
                              {String(option)}
                            </button>

                          )
                        )}

                      </div>

                    )}

                </div>

                {/* =================================================
                    PRODUCT DETAILS CARDS
                ================================================= */}
                {chatMessage.sender === "ai" &&
                  chatMessage.presentationFormat === "card" &&
                  Array.isArray(
                    chatMessage.frontendRecords
                  ) &&
                  chatMessage.frontendRecords.length > 0 && (

                    <div className="product-results-container">

                      {chatMessage.frontendRecords.map(
                        (
                          record,
                          recordIndex
                        ) => (

                          <ProductDetailsCard
                            key={
                              `${chatMessage.id}-product-${recordIndex}`
                            }
                            record={record}
                            index={recordIndex}
                          />

                        )
                      )}

                    </div>

                )}

                {chatMessage.sender === "ai" &&
                  chatMessage.presentationFormat === "table" &&
                  Array.isArray(
                    chatMessage.frontendRecords
                  ) &&
                  chatMessage.frontendRecords.length > 0 && (

                    <ProductDetailsTable
                      records={
                        chatMessage.frontendRecords
                      }
                    />

                )}          

              </div>

            </div>

            )
          )}

          {/* =================================================
              LOADING
          ================================================= */}

          {isLoading && (

            <div className="message-row ai-row">

              <div className="message-bubble ai-bubble">
                Thinking...
              </div>

            </div>

          )}

          {/* =================================================
              SCROLL TARGET
          ================================================= */}

          <div ref={messagesEndRef} />

        </div>

        {/* =================================================
            INPUT AREA
        ================================================= */}

        <div className="chat-input-area">

          <div className="input-wrapper">

            {/* Microphone */}

            <button
              className={
                isRecording
                  ? "mic-button recording"
                  : isVoiceProcessing
                  ? "mic-button voice-processing"
                  : "mic-button"
              }
              title={
                isRecording
                  ? "Stop recording"
                  : isVoiceProcessing
                  ? "Converting voice to text..."
                  : "Voice input"
              }
              type="button"
              disabled={isLoading || isVoiceProcessing}
              onClick={
                isRecording
                  ? stopRecording
                  : startRecording
              }
            >
              {isRecording ? (
                "⏹"
              ) : isVoiceProcessing ? (
                <span className="voice-search-loader"></span>
              ) : (
                "🎙"
              )}
            </button>

            {/* Text input */}

            <input
              type="text"
              value={message}
              onChange={(event) =>
                setMessage(
                  event.target.value
                )
              }
              onKeyDown={handleKeyDown}
              placeholder="Type your message..."
              disabled={isLoading}
            />

            {/* Send */}

            <button
              className="send-button"
              onClick={() =>
                sendMessage()
              }
              title="Send"
              type="button"
              disabled={
                isLoading ||
                !message.trim()
              }
            >
              ➤
            </button>

          </div>

        </div>

      </div>

    </div>
  );
}

export default App;