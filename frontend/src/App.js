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
        alert('Audio uploaded successfully!');
      } else {
        const error = await response.json();
        alert(`Upload failed: ${error.detail}`);
      }
    } catch (error) {
      console.error('Upload error:', error);
      alert('Upload failed');
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
        alert('Category created successfully!');
      } else {
        const error = await response.json();
        alert(`Failed to create category: ${error.detail}`);
      }
    } catch (error) {
      console.error('Category creation error:', error);
      alert('Failed to create category');
    }
  };

  // Delete audio file
  const deleteAudioFile = async (fileId) => {
    if (!window.confirm('Are you sure you want to delete this audio file?')) {
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
        alert('Audio file deleted successfully!');
      } else {
        alert('Failed to delete audio file');
      }
    } catch (error) {
      console.error('Delete error:', error);
      alert('Failed to delete audio file');
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
              All Categories
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
            <p className="text-gray-400 text-lg">No audio files found</p>
            <p className="text-gray-500 mt-2">Upload your first audio file to get started!</p>
          </div>
        )}
      </div>

      {/* Audio Player */}
      {currentAudio && (
        <div className="fixed bottom-0 left-0 right-0 bg-black bg-opacity-95 backdrop-blur-md border-t border-gray-800 p-4">
          <div className="max-w-7xl mx-auto">
            <div className="flex items-center space-x-4">
              <div className="flex-1">
                <h4 className="font-semibold text-white">{currentAudio.title}</h4>
                <p className="text-sm text-gray-400">{currentAudio.category}</p>
              </div>
              
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => {
                    if (audioRef.current) {
                      audioRef.current.currentTime = Math.max(0, audioRef.current.currentTime - 10);
                    }
                  }}
                  className="p-2 text-gray-400 hover:text-white transition-colors"
                >
                  ⏪
                </button>
                
                <button
                  onClick={() => playAudio(currentAudio)}
                  className="w-12 h-12 bg-green-600 hover:bg-green-700 rounded-full flex items-center justify-center transition-colors"
                >
                  {isPlaying ? '⏸️' : '▶️'}
                </button>
                
                <button
                  onClick={() => {
                    if (audioRef.current) {
                      audioRef.current.currentTime = Math.min(duration, audioRef.current.currentTime + 10);
                    }
                  }}
                  className="p-2 text-gray-400 hover:text-white transition-colors"
                >
                  ⏩
                </button>
                
                <button
                  onClick={stopAudio}
                  className="p-2 text-gray-400 hover:text-white transition-colors"
                >
                  ⏹️
                </button>
              </div>
              
              <div className="flex items-center space-x-2 flex-1 max-w-md">
                <span className="text-xs text-gray-400 w-12">{formatTime(currentTime)}</span>
                <div 
                  className="flex-1 h-2 bg-gray-700 rounded-full cursor-pointer"
                  onClick={handleSeek}
                >
                  <div 
                    className="h-full bg-green-600 rounded-full"
                    style={{ width: `${duration ? (currentTime / duration) * 100 : 0}%` }}
                  />
                </div>
                <span className="text-xs text-gray-400 w-12">{formatTime(duration)}</span>
              </div>
              
              <div className="flex items-center space-x-2">
                <span className="text-xs text-gray-400">🔊</span>
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
                  className="w-20"
                />
                
                <select
                  value={playbackRate}
                  onChange={(e) => {
                    const rate = parseFloat(e.target.value);
                    setPlaybackRate(rate);
                    if (audioRef.current) {
                      audioRef.current.playbackRate = rate;
                    }
                  }}
                  className="bg-gray-800 text-white text-xs rounded px-2 py-1"
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
            <h2 className="text-xl font-bold mb-4 text-white">Upload Audio File</h2>
            <form onSubmit={handleFileUpload} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Audio File (WAV, max 10MB)
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
                <label className="block text-sm font-medium text-gray-300 mb-2">Title</label>
                <input
                  type="text"
                  name="title"
                  required
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                  placeholder="Enter audio title"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Category</label>
                <select
                  name="category"
                  required
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                >
                  <option value="">Select a category</option>
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
                  Upload
                </button>
                <button
                  type="button"
                  onClick={() => setUploadModalOpen(false)}
                  className="flex-1 px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg font-medium transition-colors"
                >
                  Cancel
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
            <h2 className="text-xl font-bold mb-4 text-white">Create Category</h2>
            <form onSubmit={handleCreateCategory} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Category Name</label>
                <input
                  type="text"
                  name="name"
                  required
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                  placeholder="Enter category name"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Color</label>
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
                  Create
                </button>
                <button
                  type="button"
                  onClick={() => setCategoryModalOpen(false)}
                  className="flex-1 px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg font-medium transition-colors"
                >
                  Cancel
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