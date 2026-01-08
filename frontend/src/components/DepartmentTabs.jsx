import clsx from 'clsx';
import { FolderOpen, AlertTriangle } from 'lucide-react';

function DepartmentTabs({ departments, activeTab, onTabChange, userDepartment }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-1">
      <nav className="flex space-x-1">
        {departments.map((dept) => {
          const isUserDept = dept === userDepartment;
          const isActive = dept === activeTab;

          return (
            <button
              key={dept}
              onClick={() => onTabChange(dept)}
              className={clsx(
                'flex items-center px-4 py-2.5 text-sm font-medium rounded-lg transition-all',
                isActive
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              )}
            >
              <FolderOpen className={clsx('w-4 h-4 mr-2', isActive ? 'text-white' : 'text-gray-400')} />
              {dept}
              {isUserDept && (
                <span
                  className={clsx(
                    'ml-2 px-1.5 py-0.5 text-xs rounded',
                    isActive ? 'bg-blue-500 text-white' : 'bg-blue-100 text-blue-600'
                  )}
                >
                  You
                </span>
              )}
              {!isUserDept && !isActive && (
                <AlertTriangle className="w-3 h-3 ml-1.5 text-amber-500" />
              )}
            </button>
          );
        })}
      </nav>
    </div>
  );
}

export default DepartmentTabs;
