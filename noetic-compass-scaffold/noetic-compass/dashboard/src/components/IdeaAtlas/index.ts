/**
 * Public re-exports for the IdeaAtlas component family.
 *
 * Consumers should import from this barrel:
 *
 *   import {
 *     IdeaAtlasView,
 *     DiagramView,
 *     ViewToggle,
 *     InfiniteCanvas,
 *     STUB_ATLAS,
 *   } from '@/components/IdeaAtlas';
 *
 * Types live in ./types and are re-exported here for convenience.
 */

export { IdeaAtlasView } from './IdeaAtlasView';
export type { IdeaAtlasViewProps } from './IdeaAtlasView';

export { DiagramView } from './DiagramView';
export type { DiagramViewProps } from './DiagramView';

export { ViewToggle } from './ViewToggle';
export type { ViewToggleProps } from './ViewToggle';

export { InfiniteCanvas } from './InfiniteCanvas';
export type { InfiniteCanvasProps } from './InfiniteCanvas';

export { STUB_ATLAS, STUB_DIAGRAM, STUB_TRACE } from './stubs';

export type {
  AtlasNodeClickEvent,
  AtlasSelection,
  AtlasViewMode,
  CasDiagram,
  CasPrediction,
  DiagramEdge,
  DiagramNode,
  DiagramContainer,
  DomainLabel,
  DriveLabel,
  EdgeKind,
  GenerationTrace,
  IdeaAtlas,
  IdeaAtlasContext,
  IdeaEdge,
  IdeaNode,
  NoeticToken,
  NoeticName,
  RegisterLabel,
  RegisterMode,
  ViewportTransform,
} from './types';

export {
  DOMAIN_LABELS,
  DRIVE_LABELS,
  EDGE_KINDS,
  NOETIC_LABELS,
  REGISTER_LABELS,
  REGISTER_MODE_LABELS,
  isGenerationId,
} from './types';
