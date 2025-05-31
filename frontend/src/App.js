import React, { useState, useEffect, useRef } from 'react';
import './App.css';

function App() {
  const [audioFiles, setAudioFiles] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [currentAudio, setCurrentAudio] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [categoryModalOpen, setCategoryModalOpen] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [playbackRate, setPlaybackRate] = useState(1);
  
  const audioRef = useRef(null);
  const fileInputRef = useRef(null);
  
  const backendUrl = process.env.REACT_APP_BACKEND_URL;

  // Fetch audio files
  const fetchAudioFiles = async (category = '') => {
    try {
      const url = category 
        ? `${backendUrl}/api/audio-files?category=${encodeURIComponent(category)}`
        : `${backendUrl}/api/audio-files`;
      
      const response = await fetch(url);
      const data = await response.json();
      setAudioFiles(data.audio_files || []);
    } catch (error) {
      console.error('Error fetching audio files:', error);
    }
  };

  // Fetch categories
  const fetchCategories = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/categories`);
      const data = await response.json();
      setCategories(data.categories || []);
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  };

  useEffect(() => {
    fetchAudioFiles();
    fetchCategories();
  }, []);

  useEffect(() => {
    fetchAudioFiles(selectedCategory);
  }, [selectedCategory]);

  // Audio player controls
  const playAudio = (audioFile) => {
    if (currentAudio && currentAudio.id === audioFile.id) {
      if (isPlaying) {
        audioRef.current.pause();
        setIsPlaying(false);
      } else {
        audioRef.current.play();
        setIsPlaying(true);
      }
    } else {
      setCurrentAudio(audioFile);
      setIsPlaying(true);
    }
  };

  const stopAudio = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setIsPlaying(false);
    setCurrentTime(0);
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration);
    }
  };

  const handleSeek = (e) => {
    const progressBar = e.currentTarget;
    const clickX = e.nativeEvent.offsetX;
    const width = progressBar.offsetWidth;
    const newTime = (clickX / width) * duration;
    
    if (audioRef.current) {
      audioRef.current.currentTime = newTime;
      setCurrentTime(newTime);
    }
  };

  const formatTime = (time) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  // Upload functionality
  const handleFileUpload = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    try {
      const response = await fetch(`${backendUrl}/api/upload-audio`, {
        method: 'POST',
        body: formData,
      });
      
      if (response.ok) {
        setUploadModalOpen(false);
        fetchAudioFiles(selectedCategory);
        e.target.reset();
        alert('音声ファイルが正常にアップロードされました！');
      } else {
        const error = await response.json();
        alert(`アップロードに失敗しました: ${error.detail}`);
      }
    } catch (error) {
      console.error('Upload error:', error);
      alert('アップロードに失敗しました');
    }
  };

  // Category creation
  const handleCreateCategory = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    try {
      const response = await fetch(`${backendUrl}/api/categories`, {
        method: 'POST',
        body: formData,
      });
      
      if (response.ok) {
        setCategoryModalOpen(false);
        fetchCategories();
        e.target.reset();
        alert('カテゴリが正常に作成されました！');
      } else {
        const error = await response.json();
        alert(`カテゴリの作成に失敗しました: ${error.detail}`);
      }
    } catch (error) {
      console.error('Category creation error:', error);
      alert('カテゴリの作成に失敗しました');
    }
  };

  // Delete audio file
  const deleteAudioFile = async (fileId) => {
    if (!window.confirm('この音声ファイルを削除してもよろしいですか？')) {
      return;
    }
    
    try {
      const response = await fetch(`${backendUrl}/api/audio-file/${fileId}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        fetchAudioFiles(selectedCategory);
        if (currentAudio && currentAudio.id === fileId) {
          setCurrentAudio(null);
          setIsPlaying(false);
        }
        alert('音声ファイルが正常に削除されました！');
      } else {
        alert('音声ファイルの削除に失敗しました');
      }
    } catch (error) {
      console.error('Delete error:', error);
      alert('音声ファイルの削除に失敗しました');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-black text-white">
      {/* Header */}
      <header className="bg-black bg-opacity-50 backdrop-blur-md border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-green-400">🎧 ポッドキャストハブ</h1>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setCategoryModalOpen(true)}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg font-medium transition-colors"
              >
                カテゴリ追加
              </button>
              <button
                onClick={() => setUploadModalOpen(true)}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg font-medium transition-colors"
              >
                音声アップロード
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Category Filter */}
        <div className="mb-8">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setSelectedCategory('')}
              className={`px-4 py-2 rounded-full font-medium transition-colors ${
                selectedCategory === '' 
                  ? 'bg-green-600 text-white' 
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              全てのカテゴリ
            </button>
            {categories.map((category) => (
              <button
                key={category.id}
                onClick={() => setSelectedCategory(category.name)}
                className={`px-4 py-2 rounded-full font-medium transition-colors ${
                  selectedCategory === category.name
                    ? 'bg-green-600 text-white'
                    : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                }`}
                style={{
                  backgroundColor: selectedCategory === category.name ? category.color : undefined
                }}
              >
                {category.name}
              </button>
            ))}
          </div>
        </div>

        {/* Audio Files Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {audioFiles.map((audio) => (
            <div key={audio.id} className="bg-gray-800 rounded-xl p-6 hover:bg-gray-700 transition-colors">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-white mb-2">{audio.title}</h3>
                  <p className="text-gray-400 text-sm">{audio.category}</p>
                  <p className="text-gray-500 text-xs mt-1">
                    {new Date(audio.uploaded_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  onClick={() => deleteAudioFile(audio.id)}
                  className="text-red-400 hover:text-red-300 transition-colors"
                >
                  🗑️
                </button>
              </div>
              
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => playAudio(audio)}
                  className="flex-shrink-0 w-12 h-12 bg-green-600 hover:bg-green-700 rounded-full flex items-center justify-center transition-colors"
                >
                  {currentAudio && currentAudio.id === audio.id && isPlaying ? '⏸️' : '▶️'}
                </button>
                <div className="flex-1">
                  <div className="text-sm text-gray-400">
                    {audio.original_filename}
                  </div>
                  <div className="text-xs text-gray-500">
                    {(audio.file_size / (1024 * 1024)).toFixed(2)} MB
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {audioFiles.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-400 text-lg">音声ファイルが見つかりません</p>
            <p className="text-gray-500 mt-2">最初の音声ファイルをアップロードして始めましょう！</p>
          </div>
        )}
      </div>

      {/* Audio Player */}
      {currentAudio && (
        <div className="fixed bottom-0 left-0 right-0 bg-gradient-to-r from-gray-900 via-black to-gray-900 backdrop-blur-xl border-t border-gray-700 shadow-2xl">
          <div className="max-w-7xl mx-auto px-6 py-4">
            {/* Progress Bar - Top */}
            <div className="mb-4">
              <div 
                className="w-full h-1 bg-gray-700 rounded-full cursor-pointer hover:h-2 transition-all duration-200"
                onClick={handleSeek}
              >
                <div 
                  className="h-full bg-gradient-to-r from-green-400 to-green-600 rounded-full shadow-lg"
                  style={{ width: `${duration ? (currentTime / duration) * 100 : 0}%` }}
                />
              </div>
            </div>
            
            <div className="flex items-center justify-between">
              {/* Current Track Info */}
              <div className="flex items-center space-x-4 flex-1 min-w-0">
                <div className="w-14 h-14 bg-gradient-to-br from-green-500 to-green-700 rounded-xl flex items-center justify-center shadow-lg">
                  <span className="text-2xl">🎵</span>
                </div>
                <div className="min-w-0 flex-1">
                  <h4 className="font-bold text-white text-lg truncate">{currentAudio.title}</h4>
                  <p className="text-green-400 text-sm font-medium">{currentAudio.category}</p>
                </div>
              </div>
              
              {/* Main Controls */}
              <div className="flex items-center space-x-6 mx-8">
                <button
                  onClick={() => {
                    if (audioRef.current) {
                      audioRef.current.currentTime = Math.max(0, audioRef.current.currentTime - 10);
                    }
                  }}
                  className="p-3 text-gray-300 hover:text-white hover:bg-gray-800 rounded-full transition-all duration-200 transform hover:scale-110"
                  title="10秒戻る"
                >
                  <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M11.99 5V1l-5 5 5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6h-2c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/>
                    <text x="12" y="15" textAnchor="middle" fontSize="8" fill="white">10</text>
                  </svg>
                </button>
                
                <button
                  onClick={() => playAudio(currentAudio)}
                  className="w-16 h-16 bg-gradient-to-r from-green-500 to-green-600 hover:from-green-400 hover:to-green-500 rounded-full flex items-center justify-center shadow-2xl transition-all duration-300 transform hover:scale-110"
                >
                  <span className="text-3xl text-white">
                    {isPlaying ? '⏸️' : '▶️'}
                  </span>
                </button>
                
                <button
                  onClick={() => {
                    if (audioRef.current) {
                      audioRef.current.currentTime = Math.min(duration, audioRef.current.currentTime + 10);
                    }
                  }}
                  className="p-3 text-gray-300 hover:text-white hover:bg-gray-800 rounded-full transition-all duration-200 transform hover:scale-110"
                  title="10秒進む"
                >
                  <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 5V1l5 5-5 5V7c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6h2c0 4.42-3.58 8-8 8s-8-3.58-8-8 3.58-8 8-8z"/>
                    <text x="12" y="15" textAnchor="middle" fontSize="8" fill="white">10</text>
                  </svg>
                </button>
              </div>
              
              {/* Time and Extra Controls */}
              <div className="flex items-center space-x-6 flex-1 justify-end">
                <div className="flex items-center space-x-2 text-sm text-gray-300">
                  <span className="font-mono">{formatTime(currentTime)}</span>
                  <span>/</span>
                  <span className="font-mono">{formatTime(duration)}</span>
                </div>
                
                <div className="flex items-center space-x-3">
                  <button
                    onClick={stopAudio}
                    className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-all duration-200"
                    title="停止"
                  >
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                      <rect x="6" y="6" width="12" height="12" rx="2"/>
                    </svg>
                  </button>
                  
                  <div className="flex items-center space-x-2">
                    <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
                    </svg>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.1"
                      value={volume}
                      onChange={(e) => {
                        const newVolume = parseFloat(e.target.value);
                        setVolume(newVolume);
                        if (audioRef.current) {
                          audioRef.current.volume = newVolume;
                        }
                      }}
                      className="w-20 audio-slider"
                    />
                  </div>
                  
                  <select
                    value={playbackRate}
                    onChange={(e) => {
                      const rate = parseFloat(e.target.value);
                      setPlaybackRate(rate);
                      if (audioRef.current) {
                        audioRef.current.playbackRate = rate;
                      }
                    }}
                    className="bg-gray-800 hover:bg-gray-700 text-white text-sm rounded-lg px-3 py-2 border border-gray-600 focus:border-green-500 transition-colors"
                  >
                    <option value="0.5">0.5x</option>
                    <option value="0.75">0.75x</option>
                    <option value="1">1x</option>
                    <option value="1.25">1.25x</option>
                    <option value="1.5">1.5x</option>
                    <option value="2">2x</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
          
          <audio
            ref={audioRef}
            src={currentAudio ? `${backendUrl}${currentAudio.file_url}` : ''}
            onTimeUpdate={handleTimeUpdate}
            onLoadedMetadata={handleLoadedMetadata}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            volume={volume}
            preload="metadata"
          />
        </div>
      )}

      {/* Upload Modal */}
      {uploadModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4 text-white">音声ファイルをアップロード</h2>
            <form onSubmit={handleFileUpload} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  音声ファイル（WAV、最大10MB）
                </label>
                <input
                  ref={fileInputRef}
                  type="file"
                  name="file"
                  accept=".wav"
                  required
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">タイトル</label>
                <input
                  type="text"
                  name="title"
                  required
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                  placeholder="音声のタイトルを入力"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">カテゴリ</label>
                <select
                  name="category"
                  required
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                >
                  <option value="">カテゴリを選択</option>
                  {categories.map((category) => (
                    <option key={category.id} value={category.name}>
                      {category.name}
                    </option>
                  ))}
                </select>
              </div>
              
              <div className="flex space-x-4">
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg font-medium transition-colors"
                >
                  アップロード
                </button>
                <button
                  type="button"
                  onClick={() => setUploadModalOpen(false)}
                  className="flex-1 px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg font-medium transition-colors"
                >
                  キャンセル
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Category Modal */}
      {categoryModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4 text-white">カテゴリを作成</h2>
            <form onSubmit={handleCreateCategory} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">カテゴリ名</label>
                <input
                  type="text"
                  name="name"
                  required
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                  placeholder="カテゴリ名を入力"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">色</label>
                <input
                  type="color"
                  name="color"
                  defaultValue="#3B82F6"
                  className="w-full h-10 bg-gray-700 border border-gray-600 rounded-lg"
                />
              </div>
              
              <div className="flex space-x-4">
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg font-medium transition-colors"
                >
                  作成
                </button>
                <button
                  type="button"
                  onClick={() => setCategoryModalOpen(false)}
                  className="flex-1 px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg font-medium transition-colors"
                >
                  キャンセル
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;