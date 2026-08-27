import "./App.css";

import RosterSetup from "./components/RosterSetup";
import TeamMembers from "./components/TeamMembers";


function App() {
  return (
    <div>
      <RosterSetup />
      <hr />
      <TeamMembers />
    </div>
  );
}


export default App;