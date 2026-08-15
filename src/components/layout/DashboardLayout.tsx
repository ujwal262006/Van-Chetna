import { ReactNode } from 'react';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import { ConnectionState } from '../../types';

interface Props {
  children: ReactNode;
  title: string;
  connectionState: ConnectionState;
  alertCount?: number;
}

export default function DashboardLayout({ children, title, connectionState, alertCount }: Props) {
  return (
    <div className="h-screen flex overflow-hidden bg-gray-50 dark:bg-[#080b0f]">
      <Sidebar connectionState={connectionState} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar title={title} connectionState={connectionState} alertCount={alertCount} />
        <main className="flex-1 overflow-y-auto p-5">
          {children}
        </main>
      </div>
    </div>
  );
}
