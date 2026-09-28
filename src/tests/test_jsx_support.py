import os
import shutil
import tempfile
import unittest
from build_graph import build_graph

class TestJSXSupport(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.jsx_file = os.path.join(self.temp_dir, "UserDashboard.jsx").replace("\\", "/")
        with open(self.jsx_file, "w", encoding="utf-8") as f:
            f.write('''
import React, { useState, useEffect } from 'react';
import UserProfile from './UserProfile';

export default function UserDashboard({ userId, onUpdate }) {
  const [user, setUser] = useState(null);

  useEffect(() => {
    fetchUser(userId).then(data => setUser(data));
  }, [userId]);

  const handleSave = (updatedData) => {
    onUpdate(updatedData);
  };

  return (
    <div className="dashboard">
      <Header title="User Dashboard" />
      <UserProfile user={user} onSave={handleSave} />
    </div>
  );
}
''')

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_jsx_component_and_param_extraction(self):
        graph = build_graph(self.temp_dir)
        self.assertIsNotNone(graph)
        
        # Verify destructured parameter extraction (userId, onUpdate) for UserDashboard
        file_key = next((k for k in graph["parameters"] if k.lower().endswith("userdashboard.jsx")), None)
        self.assertIsNotNone(file_key, f"UserDashboard.jsx file key missing in graph parameters keys: {list(graph['parameters'].keys())}")
        params_list = graph["parameters"].get(file_key, [])

        dashboard_entry = next((p for p in params_list if p["function"] == "UserDashboard"), None)
        self.assertIsNotNone(dashboard_entry, f"UserDashboard function entry missing from parameters for {file_key}")
        self.assertIn("userId", dashboard_entry["params"])
        self.assertIn("onUpdate", dashboard_entry["params"])

        # Verify handleSave parameter extraction
        save_entry = next((p for p in params_list if p["function"] == "handleSave"), None)
        self.assertIsNotNone(save_entry, f"handleSave function entry missing from parameters for {file_key}")
        self.assertIn("updatedData", save_entry["params"])

        # Verify call extraction (useState, useEffect, fetchUser, onUpdate)
        file_key_calls = next((k for k in graph["calls"] if k.lower().endswith("userdashboard.jsx")), None)
        calls = [c.get("call") or c.get("target") or c.get("function") for c in graph["calls"].get(file_key_calls, [])]



        self.assertIn("useState", calls)
        self.assertIn("useEffect", calls)
        self.assertIn("fetchUser", calls)
        self.assertIn("onUpdate", calls)

if __name__ == "__main__":
    unittest.main()
