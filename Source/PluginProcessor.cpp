#include "PluginProcessor.h"
#include "PluginEditor.h"

juce::AudioProcessorValueTreeState::ParameterLayout VstAiDemoAudioProcessor::createParameterLayout()
{
    juce::AudioProcessorValueTreeState::ParameterLayout layout;

    layout.add(std::make_unique<juce::AudioParameterFloat>(
        "mix", "Wet/Dry Mix", 0.0f, 1.0f, 0.33f));

    layout.add(std::make_unique<juce::AudioParameterFloat>(
        "decay", "Decay Time", 0.1f, 2.0f, 0.5f));

    return layout;
}

VstAiDemoAudioProcessor::VstAiDemoAudioProcessor()
    : AudioProcessor(BusesProperties()
          .withInput("Input", juce::AudioChannelSet::stereo(), true)
          .withOutput("Output", juce::AudioChannelSet::stereo(), true)),
      apvts(*this, nullptr, "Parameters", createParameterLayout())
{
}

void VstAiDemoAudioProcessor::prepareToPlay(double sampleRate, int samplesPerBlock)
{
    juce::ignoreUnused(samplesPerBlock);

    reverbL.setSampleRate(sampleRate);
    reverbR.setSampleRate(sampleRate);

    juce::Reverb::Parameters params;
    params.dampening = 0.5f;
    params.freezeMode = 0.0f;
    params.roomSize = 0.5f;
    params.width = 1.0f;
    params.wetLevel = 0.33f;
    params.dryLevel = 0.4f;

    reverbL.setParameters(params);
    reverbR.setParameters(params);
}

void VstAiDemoAudioProcessor::releaseResources()
{
}

bool VstAiDemoAudioProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const
{
    const auto input = layouts.getMainInputChannelSet();
    const auto output = layouts.getMainOutputChannelSet();
    return input == output &&
           (output == juce::AudioChannelSet::mono() ||
            output == juce::AudioChannelSet::stereo());
}

void VstAiDemoAudioProcessor::processBlock(juce::AudioBuffer<float>& buffer,
                                            juce::MidiBuffer& midiMessages)
{
    juce::ScopedNoDenormals noDenormals;
    juce::ignoreUnused(midiMessages);

    auto* mixParam = dynamic_cast<juce::AudioParameterFloat*>(
        apvts.getParameter("mix"));
    auto* decayParam = dynamic_cast<juce::AudioParameterFloat*>(
        apvts.getParameter("decay"));

    if (mixParam == nullptr || decayParam == nullptr)
        return;

    float mix = mixParam->get();
    float decay = decayParam->get();

    // Update reverb parameters based on decay time
    juce::Reverb::Parameters params;
    params.dampening = 0.5f;
    params.freezeMode = 0.0f;
    params.roomSize = decay * 0.5f;  // Scale decay to room size
    params.width = 1.0f;
    params.wetLevel = mix;           // Wet level based on mix
    params.dryLevel = 1.0f - mix;    // Dry level inverse of mix

    reverbL.setParameters(params);
    reverbR.setParameters(params);

    if (buffer.getNumChannels() >= 2)
    {
        auto* channelL = buffer.getWritePointer(0);
        auto* channelR = buffer.getWritePointer(1);
        reverbL.processStereo(channelL, channelR, buffer.getNumSamples());
    }
    else if (buffer.getNumChannels() == 1)
    {
        auto* channel = buffer.getWritePointer(0);
        reverbL.processMono(channel, buffer.getNumSamples());
    }
}

juce::AudioProcessorEditor* VstAiDemoAudioProcessor::createEditor()
{
    return new VstAiDemoAudioProcessorEditor(*this);
}

void VstAiDemoAudioProcessor::getStateInformation(juce::MemoryBlock& destData)
{
    auto state = apvts.copyState();
    std::unique_ptr<juce::XmlElement> xml(state.createXml());
    copyXmlToBinary(*xml, destData);
}

void VstAiDemoAudioProcessor::setStateInformation(const void* data, int sizeInBytes)
{
    std::unique_ptr<juce::XmlElement> xmlState(getXmlFromBinary(data, sizeInBytes));
    if (xmlState.get() != nullptr)
    {
        if (xmlState->hasTagName(apvts.state.getType()))
        {
            apvts.replaceState(juce::ValueTree::fromXml(*xmlState));
        }
    }
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new VstAiDemoAudioProcessor();
}
