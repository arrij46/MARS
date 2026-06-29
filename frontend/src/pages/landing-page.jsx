import NavigationBar from '../components/NavigationBar';
import Hero from '../components/landing-page/Hero';
import Features from '../components/landing-page/Features';
import Users from '../components/landing-page/Users';
import Workflow from '../components/landing-page/Workflow';
import Demo from "../components/landing-page/Demo";
import Footer from '../components/Footer';
export default function LandingPage(){
    return (
        <div className='landing-page-container'>
        <NavigationBar/>
        <Hero/>
        <Features/>
        <Users/>
        <Workflow/>
        <Demo/>
        <Footer/>
        </div>
    );
}