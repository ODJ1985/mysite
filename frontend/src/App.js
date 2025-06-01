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
      setIsPlaying(false);
      // Use setTimeout to ensure the audio element is updated with new src
      setTimeout(() => {
        if (audioRef.current) {
          audioRef.current.play().then(() => {
            setIsPlaying(true);
          }).catch((error) => {
            console.error('Error playing audio:', error);
          });
        }
      }, 100);
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
    const fileInput = formData.get('file');
    
    // Check file size before upload (7MB limit - current server constraint)
    if (fileInput && fileInput.size > 7 * 1024 * 1024) {
      alert('ファイルサイズが7MBを超えています。より小さなファイルを選択してください。');
      return;
    }
    
    // Show loading state
    const submitButton = e.target.querySelector('button[type="submit"]');
    const originalText = submitButton.textContent;
    submitButton.textContent = 'アップロード中...';
    submitButton.disabled = true;
    
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
      alert('アップロードに失敗しました。ネットワーク接続を確認してください。');
    } finally {
      // Reset button state
      submitButton.textContent = originalText;
      submitButton.disabled = false;
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

  // Delete category functionality
  const deleteCategory = async (categoryName) => {
    if (!window.confirm(`カテゴリ「${categoryName}」を削除してもよろしいですか？\n\n注意：このカテゴリに音声ファイルがある場合は削除できません。`)) {
      return;
    }
    
    try {
      const response = await fetch(`${backendUrl}/api/categories/${encodeURIComponent(categoryName)}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        fetchCategories();
        // If the deleted category was selected, reset to "all"
        if (selectedCategory === categoryName) {
          setSelectedCategory('');
        }
        alert('カテゴリが正常に削除されました！');
      } else {
        const error = await response.json();
        alert(`カテゴリの削除に失敗しました: ${error.detail}`);
      }
    } catch (error) {
      console.error('Delete category error:', error);
      alert('カテゴリの削除に失敗しました');
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
    <div className="min-h-screen bg-gray-200 text-gray-700">
      {/* Header */}
      <header className="bg-gray-200 border-b border-gray-300 neumorphic" style={{borderRadius: '0 0 30px 30px', margin: '0 10px'}}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row items-center justify-between py-4 sm:h-20">
            <div className="flex items-center mb-3 sm:mb-0">
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-700">🎧 wyEBIYA Podcast</h1>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-4">
              <button
                onClick={() => window.open('/preview.html', '_blank')}
                className="px-4 py-2 sm:px-6 sm:py-3 neumorphic-button font-medium text-gray-700 text-sm sm:text-base"
              >
                📱 プレビュー
              </button>
              <button
                onClick={() => setCategoryModalOpen(true)}
                className="px-4 py-2 sm:px-6 sm:py-3 neumorphic-button font-medium text-gray-700 text-sm sm:text-base"
              >
                カテゴリ追加
              </button>
              <button
                onClick={() => setUploadModalOpen(true)}
                className="px-4 py-2 sm:px-6 sm:py-3 neumorphic-button font-medium text-gray-700 text-sm sm:text-base"
              >
                音声アップロード
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Category Filter */}
        <div className="mb-6">
          <div className="flex flex-wrap gap-2 sm:gap-4 justify-center sm:justify-start">
            <button
              onClick={() => setSelectedCategory('')}
              className={`px-3 py-2 sm:px-6 sm:py-3 text-sm sm:text-base font-medium transition-all duration-300 ${
                selectedCategory === '' 
                  ? 'neumorphic-inset text-blue-600' 
                  : 'neumorphic-button text-gray-700'
              }`}
            >
              全て
            </button>
            {categories.map((category) => (
              <div key={category.id} className="flex items-center group">
                <button
                  onClick={() => setSelectedCategory(category.name)}
                  className={`px-3 py-2 sm:px-6 sm:py-3 text-sm sm:text-base font-medium transition-all duration-300 ${
                    selectedCategory === category.name
                      ? 'neumorphic-inset text-blue-600'
                      : 'neumorphic-button text-gray-700'
                  }`}
                  style={{borderRadius: '12px 0 0 12px'}}
                >
                  {category.name.length > 10 ? category.name.substring(0, 10) + '...' : category.name}
                </button>
                <button
                  onClick={() => deleteCategory(category.name)}
                  className="px-2 py-2 sm:px-3 sm:py-3 text-sm sm:text-base neumorphic-button text-red-500 hover:text-red-600 transition-all duration-300 opacity-0 group-hover:opacity-100"
                  style={{borderRadius: '0 12px 12px 0', marginLeft: '1px'}}
                  title={`カテゴリ「${category.name}」を削除`}
                >
                  🗑️
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Audio Files Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 lg:gap-8 mb-20 sm:mb-8">
          {audioFiles.map((audio) => (
            <div key={audio.id} className="neumorphic-card p-4 sm:p-6">
              <div className="flex items-start justify-between mb-3 sm:mb-4">
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg sm:text-xl font-semibold text-gray-700 mb-1 sm:mb-2 truncate">{audio.title}</h3>
                  <p className="text-blue-600 text-xs sm:text-sm font-medium truncate">{audio.category}</p>
                  <p className="text-gray-500 text-xs mt-1">
                    {new Date(audio.uploaded_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  onClick={() => deleteAudioFile(audio.id)}
                  className="text-red-500 hover:text-red-600 transition-colors p-2 neumorphic-button ml-2"
                >
                  🗑️
                </button>
              </div>
              
              <div className="flex items-center space-x-3 sm:space-x-4">
                <button
                  onClick={() => playAudio(audio)}
                  className="flex-shrink-0 w-12 h-12 sm:w-16 sm:h-16 neumorphic-button flex items-center justify-center"
                  style={{
                    background: currentAudio && currentAudio.id === audio.id && isPlaying 
                      ? 'linear-gradient(135deg, #3b82f6, #2563eb)' 
                      : 'var(--bg-primary)',
                    color: currentAudio && currentAudio.id === audio.id && isPlaying ? 'white' : 'var(--text-primary)'
                  }}
                >
                  <span className="text-xl sm:text-2xl">
                    {currentAudio && currentAudio.id === audio.id && isPlaying ? '⏸️' : '▶️'}
                  </span>
                </button>
                <div className="flex-1 min-w-0">
                  <div className="text-xs sm:text-sm text-gray-600 font-medium truncate">
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
          <div className="text-center py-16">
            <div className="neumorphic-card p-12 max-w-md mx-auto">
              <p className="text-gray-600 text-xl mb-2">音声ファイルが見つかりません</p>
              <p className="text-gray-500">最初の音声ファイルをアップロードして始めましょう！</p>
            </div>
          </div>
        )}
      </div>

      {/* Audio Player */}
      {currentAudio && (
        <div className="fixed bottom-0 left-0 right-0 bg-gray-200 border-t border-gray-300 neumorphic" style={{borderRadius: '30px 30px 0 0', margin: '0 10px'}}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 sm:py-6">
            {/* Progress Bar - Top */}
            <div className="mb-4 sm:mb-6">
              <div 
                className="w-full h-2 neumorphic-inset cursor-pointer hover:h-3 transition-all duration-200 relative"
                onClick={handleSeek}
                style={{borderRadius: '10px'}}
              >
                <div 
                  className="h-full bg-gradient-to-r from-blue-400 to-blue-600 rounded-full"
                  style={{ width: `${duration ? (currentTime / duration) * 100 : 0}%` }}
                />
              </div>
            </div>
            
            {/* Mobile Layout */}
            <div className="block sm:hidden">
              {/* Track Info */}
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-12 h-12 neumorphic flex items-center justify-center">
                  <span className="text-2xl">🎵</span>
                </div>
                <div className="min-w-0 flex-1">
                  <h4 className="font-bold text-gray-700 text-base truncate">{currentAudio.title}</h4>
                  <p className="text-blue-600 text-sm font-medium truncate">{currentAudio.category}</p>
                </div>
              </div>
              
              {/* Main Controls */}
              <div className="flex items-center justify-center space-x-6 mb-4">
                <button
                  onClick={() => {
                    if (audioRef.current) {
                      audioRef.current.currentTime = Math.max(0, audioRef.current.currentTime - 10);
                    }
                  }}
                  className="p-3 neumorphic-button text-gray-600 hover:text-gray-800"
                  title="10秒戻る"
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M11.99 5V1l-5 5 5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6h-2c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/>
                    <text x="12" y="15" textAnchor="middle" fontSize="6" fill="currentColor">10</text>
                  </svg>
                </button>
                
                <button
                  onClick={() => playAudio(currentAudio)}
                  className="w-16 h-16 flex items-center justify-center neumorphic-button"
                  style={{
                    background: isPlaying 
                      ? 'linear-gradient(135deg, #3b82f6, #2563eb)' 
                      : 'var(--bg-primary)',
                    color: isPlaying ? 'white' : 'var(--text-primary)'
                  }}
                >
                  <span className="text-3xl">
                    {isPlaying ? '⏸️' : '▶️'}
                  </span>
                </button>
                
                <button
                  onClick={() => {
                    if (audioRef.current) {
                      audioRef.current.currentTime = Math.min(duration, audioRef.current.currentTime + 10);
                    }
                  }}
                  className="p-3 neumorphic-button text-gray-600 hover:text-gray-800"
                  title="10秒進む"
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 5V1l5 5-5 5V7c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6h2c0 4.42-3.58 8-8 8s-8-3.58-8-8 3.58-8 8-8z"/>
                    <text x="12" y="15" textAnchor="middle" fontSize="6" fill="currentColor">10</text>
                  </svg>
                </button>
              </div>
              
              {/* Bottom Controls */}
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-xs text-gray-600 font-mono neumorphic-inset px-3 py-1">
                  <span>{formatTime(currentTime)}</span>
                  <span>/</span>
                  <span>{formatTime(duration)}</span>
                </div>
                
                <div className="flex items-center space-x-3">
                  <button
                    onClick={stopAudio}
                    className="p-2 neumorphic-button text-gray-600"
                    title="停止"
                  >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                      <rect x="6" y="6" width="12" height="12" rx="2"/>
                    </svg>
                  </button>
                  
                  <div className="flex items-center space-x-1 neumorphic-inset px-2 py-1">
                    <svg className="w-3 h-3 text-gray-600" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
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
                      className="w-16 neumorphic-slider"
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
                    className="neumorphic-inset text-gray-700 text-xs px-2 py-1 border-none focus:outline-none"
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
            
            {/* Desktop Layout */}
            <div className="hidden sm:flex items-center justify-between">
              {/* Current Track Info */}
              <div className="flex items-center space-x-4 flex-1 min-w-0">
                <div className="w-16 h-16 neumorphic flex items-center justify-center">
                  <span className="text-3xl">🎵</span>
                </div>
                <div className="min-w-0 flex-1">
                  <h4 className="font-bold text-gray-700 text-lg truncate">{currentAudio.title}</h4>
                  <p className="text-blue-600 text-sm font-medium">{currentAudio.category}</p>
                </div>
              </div>
              
              {/* Main Controls */}
              <div className="flex items-center space-x-8 mx-8">
                <button
                  onClick={() => {
                    if (audioRef.current) {
                      audioRef.current.currentTime = Math.max(0, audioRef.current.currentTime - 10);
                    }
                  }}
                  className="p-4 neumorphic-button text-gray-600 hover:text-gray-800"
                  title="10秒戻る"
                >
                  <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M11.99 5V1l-5 5 5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6h-2c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/>
                    <text x="12" y="15" textAnchor="middle" fontSize="8" fill="currentColor">10</text>
                  </svg>
                </button>
                
                <button
                  onClick={() => playAudio(currentAudio)}
                  className="w-20 h-20 flex items-center justify-center neumorphic-button"
                  style={{
                    background: isPlaying 
                      ? 'linear-gradient(135deg, #3b82f6, #2563eb)' 
                      : 'var(--bg-primary)',
                    color: isPlaying ? 'white' : 'var(--text-primary)'
                  }}
                >
                  <span className="text-4xl">
                    {isPlaying ? '⏸️' : '▶️'}
                  </span>
                </button>
                
                <button
                  onClick={() => {
                    if (audioRef.current) {
                      audioRef.current.currentTime = Math.min(duration, audioRef.current.currentTime + 10);
                    }
                  }}
                  className="p-4 neumorphic-button text-gray-600 hover:text-gray-800"
                  title="10秒進む"
                >
                  <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 5V1l5 5-5 5V7c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6h2c0 4.42-3.58 8-8 8s-8-3.58-8-8 3.58-8 8-8z"/>
                    <text x="12" y="15" textAnchor="middle" fontSize="8" fill="currentColor">10</text>
                  </svg>
                </button>
              </div>
              
              {/* Time and Extra Controls */}
              <div className="flex items-center space-x-6 flex-1 justify-end">
                <div className="flex items-center space-x-2 text-sm text-gray-600 font-mono neumorphic-inset px-4 py-2">
                  <span>{formatTime(currentTime)}</span>
                  <span>/</span>
                  <span>{formatTime(duration)}</span>
                </div>
                
                <div className="flex items-center space-x-4">
                  <button
                    onClick={stopAudio}
                    className="p-3 neumorphic-button text-gray-600 hover:text-gray-800"
                    title="停止"
                  >
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                      <rect x="6" y="6" width="12" height="12" rx="2"/>
                    </svg>
                  </button>
                  
                  <div className="flex items-center space-x-2 neumorphic-inset px-3 py-2">
                    <svg className="w-4 h-4 text-gray-600" fill="currentColor" viewBox="0 0 24 24">
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
                      className="w-20 neumorphic-slider"
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
                    className="neumorphic-inset text-gray-700 text-sm px-3 py-2 border-none focus:outline-none"
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
            src={currentAudio ? `${backendUrl}/api/audio-stream/${currentAudio.id}` : ''}
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
        <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center p-4 z-50">
          <div className="neumorphic-card p-8 w-full max-w-md">
            <h2 className="text-2xl font-bold mb-6 text-gray-700">音声ファイルをアップロード</h2>
            <form onSubmit={handleFileUpload} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-3">
                  音声ファイル（WAV、最大7MB）
                </label>
                <input
                  ref={fileInputRef}
                  type="file"
                  name="file"
                  accept=".wav"
                  required
                  className="w-full px-4 py-3 neumorphic-inset text-gray-700 focus:outline-none"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-3">タイトル</label>
                <input
                  type="text"
                  name="title"
                  required
                  className="w-full px-4 py-3 neumorphic-inset text-gray-700 focus:outline-none"
                  placeholder="音声のタイトルを入力"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-3">カテゴリ</label>
                <select
                  name="category"
                  required
                  className="w-full px-4 py-3 neumorphic-inset text-gray-700 focus:outline-none"
                >
                  <option value="">カテゴリを選択</option>
                  {categories.map((category) => (
                    <option key={category.id} value={category.name}>
                      {category.name}
                    </option>
                  ))}
                </select>
              </div>
              
              <div className="flex space-x-4 pt-4">
                <button
                  type="submit"
                  className="flex-1 px-6 py-3 neumorphic-button font-medium text-gray-700"
                >
                  アップロード
                </button>
                <button
                  type="button"
                  onClick={() => setUploadModalOpen(false)}
                  className="flex-1 px-6 py-3 neumorphic-button font-medium text-gray-700"
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
        <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center p-4 z-50">
          <div className="neumorphic-card p-8 w-full max-w-md">
            <h2 className="text-2xl font-bold mb-6 text-gray-700">カテゴリを作成</h2>
            <form onSubmit={handleCreateCategory} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-3">カテゴリ名</label>
                <input
                  type="text"
                  name="name"
                  required
                  className="w-full px-4 py-3 neumorphic-inset text-gray-700 focus:outline-none"
                  placeholder="カテゴリ名を入力"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-3">色</label>
                <input
                  type="color"
                  name="color"
                  defaultValue="#3B82F6"
                  className="w-full h-12 neumorphic-inset focus:outline-none"
                />
              </div>
              
              <div className="flex space-x-4 pt-4">
                <button
                  type="submit"
                  className="flex-1 px-6 py-3 neumorphic-button font-medium text-gray-700"
                >
                  作成
                </button>
                <button
                  type="button"
                  onClick={() => setCategoryModalOpen(false)}
                  className="flex-1 px-6 py-3 neumorphic-button font-medium text-gray-700"
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