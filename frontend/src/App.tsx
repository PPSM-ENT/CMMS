import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './stores/authStore';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Assets from './pages/Assets';
import AssetDetail from './pages/AssetDetail';
import AssetForm from './pages/AssetForm';
import WorkOrders from './pages/WorkOrders';
import WorkOrderDetail from './pages/WorkOrderDetail';
import WorkOrderForm from './pages/WorkOrderForm';
import PreventiveMaintenance from './pages/PreventiveMaintenance';
import PMForm from './pages/PMForm';
import Inventory from './pages/Inventory';
import PartForm from './pages/PartForm';
import PartDetail from './pages/PartDetail';
import PurchaseOrderForm from './pages/PurchaseOrderForm';
import PODetail from './pages/PODetail';
import StoreroomDetail from './pages/StoreroomDetail';
import Reports from './pages/Reports';
import Settings from './pages/Settings';
import UserGroups from './pages/UserGroups';
import UserGroupForm from './pages/UserGroupForm';
import UserGroupDetail from './pages/UserGroupDetail';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="assets" element={<Assets />} />
        <Route path="assets/new" element={<AssetForm />} />
        <Route path="assets/:id" element={<AssetDetail />} />
        <Route path="assets/:id/edit" element={<AssetForm />} />
        <Route path="work-orders" element={<WorkOrders />} />
        <Route path="work-orders/new" element={<WorkOrderForm />} />
        <Route path="work-orders/:id" element={<WorkOrderDetail />} />
        <Route path="work-orders/:id/edit" element={<WorkOrderForm />} />
        <Route path="pm" element={<PreventiveMaintenance />} />
        <Route path="pm/new" element={<PMForm />} />
        <Route path="inventory" element={<Inventory />} />
        <Route path="inventory/parts/new" element={<PartForm />} />
        <Route path="inventory/parts/:id" element={<PartDetail />} />
        <Route path="inventory/po/new" element={<PurchaseOrderForm />} />
        <Route path="inventory/po/:id" element={<PODetail />} />
        <Route path="inventory/storerooms/:id" element={<StoreroomDetail />} />
        <Route path="reports" element={<Reports />} />
        <Route path="settings" element={<Settings />} />
        <Route path="settings/user-groups" element={<UserGroups />} />
        <Route path="settings/user-groups/new" element={<UserGroupForm />} />
        <Route path="settings/user-groups/:id" element={<UserGroupDetail />} />
        <Route path="settings/user-groups/:id/edit" element={<UserGroupForm />} />
      </Route>
    </Routes>
  );
}

export default App;
