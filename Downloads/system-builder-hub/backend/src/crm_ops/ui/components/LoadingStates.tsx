import React from 'react';

export const SkeletonTable: React.FC = () => (
  <div className="space-y-3">
    {[...Array(5)].map((_, i) => (
      <div key={i} className="flex space-x-4">
        <div className="h-4 bg-gray-200 rounded w-1/4 animate-pulse"></div>
        <div className="h-4 bg-gray-200 rounded w-1/4 animate-pulse"></div>
        <div className="h-4 bg-gray-200 rounded w-1/4 animate-pulse"></div>
        <div className="h-4 bg-gray-200 rounded w-1/4 animate-pulse"></div>
      </div>
    ))}
  </div>
);

export const SkeletonCard: React.FC = () => (
  <div className="bg-white rounded-lg shadow p-6 space-y-4">
    <div className="h-6 bg-gray-200 rounded w-1/3 animate-pulse"></div>
    <div className="h-4 bg-gray-200 rounded w-1/2 animate-pulse"></div>
    <div className="h-4 bg-gray-200 rounded w-2/3 animate-pulse"></div>
  </div>
);

export const SkeletonKanban: React.FC = () => (
  <div className="flex space-x-4 overflow-x-auto">
    {[...Array(4)].map((_, i) => (
      <div key={i} className="flex-shrink-0 w-80 bg-gray-50 rounded-lg p-4">
        <div className="h-6 bg-gray-200 rounded w-1/2 animate-pulse mb-4"></div>
        <div className="space-y-3">
          {[...Array(3)].map((_, j) => (
            <div key={j} className="bg-white rounded p-3 space-y-2">
              <div className="h-4 bg-gray-200 rounded w-3/4 animate-pulse"></div>
              <div className="h-3 bg-gray-200 rounded w-1/2 animate-pulse"></div>
            </div>
          ))}
        </div>
      </div>
    ))}
  </div>
);

export const LoadingSpinner: React.FC = () => (
  <div className="flex justify-center items-center p-8">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
  </div>
);
