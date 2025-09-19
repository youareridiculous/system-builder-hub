'use client';

import React, { useRef, useState, useCallback } from 'react';
import { Upload, X, Image, FileText, Code, File, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

interface FileUploadItem {
  file: File;
  type: 'image' | 'document' | 'code' | 'other';
  preview?: string;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
  uploadedId?: string;
}

interface FileUploadProps {
  onFilesChange: (files: FileUploadItem[]) => void;
  maxFiles?: number;
  maxSize?: number; // in MB
  acceptedTypes?: string[];
  systemId?: string;
}

export default function FileUpload({ 
  onFilesChange, 
  maxFiles = 10, 
  maxSize = 50,
  acceptedTypes = ['image/*', '.pdf', '.doc', '.docx', '.txt', '.js', '.ts', '.tsx', '.jsx', '.html', '.css', '.json'],
  systemId
}: FileUploadProps) {
  const [files, setFiles] = useState<FileUploadItem[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const getFileType = (file: File): 'image' | 'document' | 'code' | 'other' => {
    const imageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml'];
    const documentTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
    const codeTypes = ['text/javascript', 'text/typescript', 'text/html', 'text/css', 'application/json', 'text/x-python', 'text/x-java', 'text/x-c++'];
    
    if (imageTypes.includes(file.type)) return 'image';
    if (documentTypes.includes(file.type)) return 'document';
    if (codeTypes.includes(file.type)) return 'code';
    return 'other';
  };

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'image': return <Image className="h-4 w-4 text-blue-500" />;
      case 'document': return <FileText className="h-4 w-4 text-green-500" />;
      case 'code': return <Code className="h-4 w-4 text-purple-500" />;
      default: return <File className="h-4 w-4 text-gray-500" />;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const validateFile = (file: File): string | null => {
    if (file.size > maxSize * 1024 * 1024) {
      return `File size must be less than ${maxSize}MB`;
    }
    
    if (files.length >= maxFiles) {
      return `Maximum ${maxFiles} files allowed`;
    }
    
    return null;
  };

  const uploadFile = async (fileItem: FileUploadItem): Promise<string | null> => {
    if (!systemId) return null;

    try {
      const formData = new FormData();
      formData.append('file', fileItem.file);
      formData.append('type', fileItem.type);

      const response = await fetch(`/api/system/upload-reference/${systemId}`, {
        method: 'POST',
        body: formData
      });

      const data = await response.json();
      
      if (data.success && data.file_id) {
        return data.file_id;
      } else {
        throw new Error(data.error || 'Upload failed');
      }
    } catch (error) {
      throw error;
    }
  };

  const handleFiles = useCallback(async (newFiles: File[]) => {
    const validFiles: FileUploadItem[] = [];
    
    for (const file of newFiles) {
      const error = validateFile(file);
      if (error) {
        console.warn(`File ${file.name} rejected: ${error}`);
        continue;
      }

      const fileType = getFileType(file);
      const fileItem: FileUploadItem = {
        file,
        type: fileType,
        preview: fileType === 'image' ? URL.createObjectURL(file) : undefined,
        status: 'pending'
      };

      validFiles.push(fileItem);
    }

    if (validFiles.length === 0) return;

    const updatedFiles = [...files, ...validFiles];
    setFiles(updatedFiles);
    onFilesChange(updatedFiles);

    // Auto-upload files if systemId is provided
    if (systemId) {
      for (const fileItem of validFiles) {
        setFiles(prev => prev.map(f => 
          f.file === fileItem.file ? { ...f, status: 'uploading' } : f
        ));

        try {
          const uploadedId = await uploadFile(fileItem);
          setFiles(prev => prev.map(f => 
            f.file === fileItem.file 
              ? { ...f, status: 'success', uploadedId } 
              : f
          ));
        } catch (error) {
          setFiles(prev => prev.map(f => 
            f.file === fileItem.file 
              ? { ...f, status: 'error', error: error instanceof Error ? error.message : 'Upload failed' } 
              : f
          ));
        }
      }
    }
  }, [files, systemId, maxFiles, maxSize, onFilesChange]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    handleFiles(droppedFiles);
  }, [handleFiles]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    handleFiles(selectedFiles);
  }, [handleFiles]);

  const removeFile = (index: number) => {
    const fileToRemove = files[index];
    if (fileToRemove.preview) {
      URL.revokeObjectURL(fileToRemove.preview);
    }
    
    const updatedFiles = files.filter((_, i) => i !== index);
    setFiles(updatedFiles);
    onFilesChange(updatedFiles);
  };

  const retryUpload = async (index: number) => {
    if (!systemId) return;

    const fileItem = files[index];
    setFiles(prev => prev.map((f, i) => 
      i === index ? { ...f, status: 'uploading', error: undefined } : f
    ));

    try {
      const uploadedId = await uploadFile(fileItem);
      setFiles(prev => prev.map((f, i) => 
        i === index ? { ...f, status: 'success', uploadedId } : f
      ));
    } catch (error) {
      setFiles(prev => prev.map((f, i) => 
        i === index ? { ...f, status: 'error', error: error instanceof Error ? error.message : 'Upload failed' } : f
      ));
    }
  };

  return (
    <div className="space-y-4">
      {/* Upload Area */}
      <div
        className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
          isDragOver 
            ? 'border-blue-400 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400'
        }`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <Upload className="h-8 w-8 text-gray-400 mx-auto mb-2" />
        <p className="text-sm text-gray-600 mb-2">
          Drag & drop files here, or click to browse
        </p>
        <p className="text-xs text-gray-500 mb-4">
          Max {maxFiles} files, {maxSize}MB each
        </p>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={handleFileInput}
          className="hidden"
          accept={acceptedTypes.join(',')}
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          Choose Files
        </button>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-700">Uploaded Files ({files.length})</h4>
          {files.map((fileItem, index) => (
            <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-md">
              <div className="flex items-center space-x-3">
                {fileItem.preview ? (
                  <img 
                    src={fileItem.preview} 
                    alt={fileItem.file.name}
                    className="h-8 w-8 object-cover rounded"
                  />
                ) : (
                  getFileIcon(fileItem.type)
                )}
                
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {fileItem.file.name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {formatFileSize(fileItem.file.size)} • {fileItem.type}
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                {fileItem.status === 'pending' && (
                  <span className="text-xs text-gray-500">Pending</span>
                )}
                
                {fileItem.status === 'uploading' && (
                  <div className="flex items-center space-x-1">
                    <Loader2 className="h-3 w-3 animate-spin text-blue-500" />
                    <span className="text-xs text-blue-600">Uploading...</span>
                  </div>
                )}
                
                {fileItem.status === 'success' && (
                  <div className="flex items-center space-x-1">
                    <CheckCircle className="h-3 w-3 text-green-500" />
                    <span className="text-xs text-green-600">Uploaded</span>
                  </div>
                )}
                
                {fileItem.status === 'error' && (
                  <div className="flex items-center space-x-1">
                    <AlertCircle className="h-3 w-3 text-red-500" />
                    <span className="text-xs text-red-600">Failed</span>
                    <button
                      onClick={() => retryUpload(index)}
                      className="text-xs text-blue-600 hover:text-blue-700 underline"
                    >
                      Retry
                    </button>
                  </div>
                )}
                
                <button
                  onClick={() => removeFile(index)}
                  className="text-gray-400 hover:text-red-500 transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Accepted File Types */}
      <div className="text-xs text-gray-500">
        <p className="font-medium mb-1">Accepted file types:</p>
        <div className="flex flex-wrap gap-1">
          {acceptedTypes.map((type, index) => (
            <span key={index} className="px-2 py-1 bg-gray-100 rounded text-xs">
              {type.replace('*', '')}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
