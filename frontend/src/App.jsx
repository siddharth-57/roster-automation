import "./App.css";

import RosterSetup from "./components/RosterSetup";
import TeamMembers from "./components/TeamMembers";


function App() {
  return (
    <div className="app-shell">

      <header className="app-header">
        <div className="app-header-inner">
          <h1>Roster Management</h1>
          <p>
            Create, Manage, Upload and Download Monthly Rosters
          </p>
        </div>
      </header>


      <main className="app-content">

        <RosterSetup />

        <hr className="section-divider" />

        <TeamMembers />

      </main>

    </div>
  );
}


export default App;