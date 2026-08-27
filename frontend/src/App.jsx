import "./App.css";

import RosterSetup from "./components/RosterSetup";
import TeamMembers from "./components/TeamMembers";


function App() {
  return (
    <div>
      <TeamMembers />

      <hr />

      <RosterSetup />
    </div>
  );
}


export default App;