import { BrowserRouter, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { BasketProvider } from "./context/BasketContext";
import { CustomerProvider } from "./context/CustomerContext";
import AddItemPage from "./pages/AddItemPage";
import BasketPage from "./pages/BasketPage";
import CataloguePage from "./pages/CataloguePage";
import GearDetailsPage from "./pages/GearDetailsPage";
import MyRentalsPage from "./pages/MyRentalsPage";
import NotFoundPage from "./pages/NotFoundPage";

// Task 4.5: the routes. Providers wrap everything so every page can use
// "who am I" (CustomerContext) and the basket (BasketContext).
export default function App() {
  return (
    <BrowserRouter>
      <CustomerProvider>
        <BasketProvider>
          <Layout>
            <Routes>
              <Route path="/" element={<CataloguePage />} />
              <Route path="/gear/:sku" element={<GearDetailsPage />} />
              <Route path="/me" element={<MyRentalsPage />} />
              <Route path="/basket" element={<BasketPage />} />
              <Route path="/admin/add" element={<AddItemPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </Layout>
        </BasketProvider>
      </CustomerProvider>
    </BrowserRouter>
  );
}
