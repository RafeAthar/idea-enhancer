'use client';

import { Sidebar } from './idea-enhancer/sidebar';
import { PipelineRunner } from './idea-enhancer/pipeline-runner';
import { ReportList } from './idea-enhancer/report-list';
import { ReportViewer } from './idea-enhancer/report-viewer';
import { CompareView } from './idea-enhancer/compare-view';
import { useState, useCallback } from 'react';
import type { AppTab } from '@/lib/types';

export function AppLayout() {
  const [activeTab, setActiveTab] = useState<AppTab>('pipeline');
  const [reportSlug, setReportSlug] = useState<string | null>(null);
  const [compareSlugs, setCompareSlugs] = useState<{ a: string; b: string } | null>(null);

  const handleViewReport = useCallback((slug: string) => {
    setReportSlug(slug);
    setActiveTab('report-viewer');
  }, []);

  const handleCompare = useCallback((slugA: string, slugB: string) => {
    setCompareSlugs({ a: slugA, b: slugB });
    setActiveTab('compare');
  }, []);

  const handleTabChange = useCallback((tab: AppTab) => {
    setActiveTab(tab);
    if (tab !== 'report-viewer') setReportSlug(null);
    if (tab !== 'compare') setCompareSlugs(null);
  }, []);

  const isPipelineRunning = false; // Could be connected to global state

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onTabChange={handleTabChange}
        isPipelineRunning={isPipelineRunning}
      />

      {/* Main content */}
      <main className="flex-1 min-w-0">
        {activeTab === 'pipeline' && (
          <PipelineRunner onViewReport={handleViewReport} />
        )}
        {activeTab === 'reports' && (
          <ReportList
            onViewReport={handleViewReport}
            onCompare={handleCompare}
          />
        )}
        {activeTab === 'report-viewer' && reportSlug && (
          <ReportViewer
            slug={reportSlug}
            onBack={() => handleTabChange('reports')}
          />
        )}
        {activeTab === 'compare' && compareSlugs && (
          <CompareView
            slugA={compareSlugs.a}
            slugB={compareSlugs.b}
            onBack={() => handleTabChange('reports')}
          />
        )}
      </main>
    </div>
  );
}
