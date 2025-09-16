import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { LoadingSpinner } from '../components/LoadingStates';
import { ErrorMessage } from '../components/ErrorStates';
import { trackEvent, AnalyticsEvents } from '../utils/analytics';
import { canCreate, canUpdate } from '../utils/rbac';
import { 
  Plus, 
  Calendar,
  User,
  Flag,
  Clock,
  MoreVertical,
  CheckCircle,
  Circle,
  Play
} from 'lucide-react';

interface Task {
  id: string;
  type: string;
  attributes: {
    title: string;
    description: string;
    status: string;
    priority: string;
    due_date: string;
    assignee_id: string;
    estimated_hours: number;
    actual_hours: number;
    project_id: string;
    created_at: string;
  };
}

interface Project {
  id: string;
  type: string;
  attributes: {
    name: string;
    description: string;
    status: string;
    start_date: string;
    end_date: string;
  };
}

interface TaskCardProps {
  task: Task;
  onEdit: (task: Task) => void;
  onMove: (taskId: string, newStatus: string) => void;
}

const TaskCard: React.FC<TaskCardProps> = ({ task, onEdit, onMove }) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'bg-red-100 text-red-800';
      case 'high': return 'bg-orange-100 text-orange-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'low': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'todo': return <Circle className="h-4 w-4 text-gray-400" />;
      case 'in_progress': return <Play className="h-4 w-4 text-blue-500" />;
      case 'review': return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'done': return <CheckCircle className="h-4 w-4 text-green-500" />;
      default: return <Circle className="h-4 w-4 text-gray-400" />;
    }
  };

  const isOverdue = task.attributes.due_date && 
    new Date(task.attributes.due_date) < new Date() && 
    task.attributes.status !== 'done';

  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-3 hover:shadow-md transition-shadow ${
      isOverdue ? 'border-red-300 bg-red-50' : ''
    }`}>
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center space-x-2">
          {getStatusIcon(task.attributes.status)}
          <h3 className="font-medium text-gray-900 text-sm line-clamp-2">
            {task.attributes.title}
          </h3>
        </div>
        <div className="relative">
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="text-gray-400 hover:text-gray-600"
          >
            <MoreVertical className="h-4 w-4" />
          </button>
          {isMenuOpen && (
            <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg z-10 border border-gray-200">
              <div className="py-1">
                <button
                  onClick={() => {
                    onEdit(task);
                    setIsMenuOpen(false);
                  }}
                  className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                >
                  Edit Task
                </button>
                <button
                  onClick={() => {
                    onMove(task.id, 'in_progress');
                    setIsMenuOpen(false);
                  }}
                  className="block w-full text-left px-4 py-2 text-sm text-blue-700 hover:bg-gray-100"
                >
                  Start Task
                </button>
                <button
                  onClick={() => {
                    onMove(task.id, 'done');
                    setIsMenuOpen(false);
                  }}
                  className="block w-full text-left px-4 py-2 text-sm text-green-700 hover:bg-gray-100"
                >
                  Mark Complete
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="space-y-2">
        {task.attributes.description && (
          <p className="text-sm text-gray-600 line-clamp-2">
            {task.attributes.description}
          </p>
        )}

        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="flex items-center text-sm text-gray-600">
              <User className="h-4 w-4 mr-1" />
              <span>Assignee</span>
            </div>
            <span className={`px-2 py-1 text-xs rounded-full ${getPriorityColor(task.attributes.priority)}`}>
              {task.attributes.priority}
            </span>
          </div>
          {isOverdue && (
            <span className="text-xs text-red-600 font-medium">Overdue</span>
          )}
        </div>

        {task.attributes.due_date && (
          <div className="flex items-center text-sm text-gray-600">
            <Calendar className="h-4 w-4 mr-1" />
            Due: {new Date(task.attributes.due_date).toLocaleDateString()}
          </div>
        )}

        <div className="flex items-center justify-between pt-2 border-t border-gray-100">
          <div className="flex items-center space-x-2">
            <Clock className="h-3 w-3 text-gray-400" />
            <span className="text-xs text-gray-500">
              Est: {task.attributes.estimated_hours || 0}h
            </span>
            {task.attributes.actual_hours && (
              <span className="text-xs text-gray-500">
                | Act: {task.attributes.actual_hours}h
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

interface KanbanColumnProps {
  title: string;
  status: string;
  tasks: Task[];
  onEdit: (task: Task) => void;
  onMove: (taskId: string, newStatus: string) => void;
  onAddTask: (status: string) => void;
}

const KanbanColumn: React.FC<KanbanColumnProps> = ({
  title,
  status,
  tasks,
  onEdit,
  onMove,
  onAddTask
}) => {
  const getColumnColor = (status: string) => {
    switch (status) {
      case 'todo': return 'border-gray-300';
      case 'in_progress': return 'border-blue-300';
      case 'review': return 'border-yellow-300';
      case 'done': return 'border-green-300';
      default: return 'border-gray-300';
    }
  };

  return (
    <div className={`flex-shrink-0 w-80 bg-gray-50 rounded-lg p-4 border-2 ${getColumnColor(status)}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-900">{title}</h3>
        <span className="bg-white px-2 py-1 rounded-full text-xs font-medium text-gray-600">
          {tasks.length}
        </span>
      </div>
      
      <div className="space-y-3">
        {tasks.map((task) => (
          <TaskCard
            key={task.id}
            task={task}
            onEdit={onEdit}
            onMove={onMove}
          />
        ))}
        
        {canCreate('tasks') && (
          <button
            onClick={() => onAddTask(status)}
            className="w-full p-3 border-2 border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-gray-400 hover:text-gray-600 transition-colors"
          >
            <Plus className="h-5 w-5 mx-auto mb-1" />
            <span className="text-sm">Add Task</span>
          </button>
        )}
      </div>
    </div>
  );
};

export default function ProjectKanban() {
  const [selectedProject, setSelectedProject] = useState<string>('all');
  const { data: projects } = useApi('/projects');
  const { data: tasks, error, isLoading, refetch } = useApi('/tasks');
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

  const handleEditTask = (task: Task) => {
    setSelectedTask(task);
    trackEvent(AnalyticsEvents.TASK_UPDATED, { taskId: task.id });
    // Open edit modal or guided prompt
    console.log('Opening edit task guided prompt');
  };

  const handleMoveTask = (taskId: string, newStatus: string) => {
    trackEvent(AnalyticsEvents.TASK_STATUS_CHANGED, { taskId, newStatus });
    // Update task status via API
    console.log('Moving task', taskId, 'to status', newStatus);
  };

  const handleAddTask = (status: string) => {
    trackEvent(AnalyticsEvents.TASK_CREATED, { status });
    // Open add task guided prompt
    console.log('Opening add task guided prompt for status:', status);
  };

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={refetch} />;
  }

  const allTasks = tasks?.data || [];
  const allProjects = projects?.data || [];
  
  const filteredTasks = selectedProject === 'all' 
    ? allTasks 
    : allTasks.filter((task: Task) => task.attributes.project_id === selectedProject);

  const taskStatuses = [
    { key: 'todo', title: 'To Do' },
    { key: 'in_progress', title: 'In Progress' },
    { key: 'review', title: 'Review' },
    { key: 'done', title: 'Done' }
  ];

  const tasksByStatus = taskStatuses.reduce((acc, status) => {
    acc[status.key] = filteredTasks.filter((task: Task) => 
      task.attributes.status === status.key
    );
    return acc;
  }, {} as Record<string, Task[]>);

  const totalTasks = filteredTasks.length;
  const completedTasks = tasksByStatus.done?.length || 0;
  const completionRate = totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Project Kanban</h1>
          <p className="text-gray-600">Manage tasks and track project progress</p>
        </div>
        <div className="flex items-center space-x-4">
          <select
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm"
          >
            <option value="all">All Projects</option>
            {allProjects.map((project: Project) => (
              <option key={project.id} value={project.id}>
                {project.attributes.name}
              </option>
            ))}
          </select>
          {canCreate('tasks') && (
            <button
              onClick={() => handleAddTask('todo')}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Task
            </button>
          )}
        </div>
      </div>

      {/* Project Stats */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Project Overview</h2>
        <div className="grid grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">{totalTasks}</div>
            <div className="text-sm text-gray-600">Total Tasks</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{tasksByStatus.todo?.length || 0}</div>
            <div className="text-sm text-gray-600">To Do</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-600">{tasksByStatus.in_progress?.length || 0}</div>
            <div className="text-sm text-gray-600">In Progress</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{completedTasks}</div>
            <div className="text-sm text-gray-600">Completed</div>
          </div>
        </div>
        <div className="mt-4">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>Completion Rate</span>
            <span>{completionRate.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-green-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${completionRate}%` }}
            ></div>
          </div>
        </div>
      </div>

      {/* Kanban Board */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex space-x-6 overflow-x-auto pb-4">
          {taskStatuses.map((status) => (
            <KanbanColumn
              key={status.key}
              title={status.title}
              status={status.key}
              tasks={tasksByStatus[status.key] || []}
              onEdit={handleEditTask}
              onMove={handleMoveTask}
              onAddTask={handleAddTask}
            />
          ))}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-2 bg-red-100 rounded-lg">
              <Flag className="h-6 w-6 text-red-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Urgent Tasks</p>
              <p className="text-2xl font-bold text-gray-900">
                {filteredTasks.filter((task: Task) => task.attributes.priority === 'urgent').length}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-2 bg-yellow-100 rounded-lg">
              <Calendar className="h-6 w-6 text-yellow-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Due This Week</p>
              <p className="text-2xl font-bold text-gray-900">
                {filteredTasks.filter((task: Task) => {
                  const dueDate = new Date(task.attributes.due_date);
                  const now = new Date();
                  const weekFromNow = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
                  return dueDate >= now && dueDate <= weekFromNow;
                }).length}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 rounded-lg">
              <CheckCircle className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Completed Today</p>
              <p className="text-2xl font-bold text-gray-900">
                {filteredTasks.filter((task: Task) => {
                  const completedDate = new Date(task.attributes.created_at);
                  const today = new Date();
                  return completedDate.toDateString() === today.toDateString() && 
                         task.attributes.status === 'done';
                }).length}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
